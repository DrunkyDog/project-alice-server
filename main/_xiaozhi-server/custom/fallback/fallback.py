"""
LLM Multi-tier Fallback Provider (custom) — xiaozhi-esp32-server
================================================================
รวมหลาย LLM เป็น chain เดียว: ยิงชั้นบนสุดก่อน ถ้าใช้ไม่ได้ (429/quota, 401,
5xx/503, timeout, connection ...) เลื่อนชั้นถัดไป "อัตโนมัติ"

- reuse core.utils.llm.create_instance() สร้าง sub-provider แต่ละชั้น → sub เป็น
  type อะไรก็ได้ที่ระบบรองรับ (openai, gemini, ollama, ...)
- ชั้นที่ยัง "ไม่ได้ใส่ key" (placeholder/ว่าง) จะถูกข้ามอัตโนมัติตอนโหลด →
  ตั้ง provider ทิ้งไว้ใน WebUI แล้วค่อยเติม key ทีหลังได้เลย
- streaming-safe: fallback เฉพาะเมื่อ error เกิด "ก่อน" token แรกถูกส่งออก
- per-provider cooldown: ชั้นที่เพิ่ง fail จะถูกพักชั่วคราว ไม่ยิงซ้ำทุก request

chain อ่านจาก config_json.providers (ตั้งใน WebUI ได้) — รองรับ 3 รูปแบบ:
  1) list ของ dict (มาจาก yaml/JSON)
  2) JSON array string
  3) delimited string (WebUI array field) — บรรทัดละชั้น, field คั่นด้วย |:
        label|type|model_name|base_url|api_key|max_tokens
     เช่น:  groq|openai|llama-3.3-70b-versatile|https://api.groq.com/openai/v1|gsk_xxx
ถ้า config ไม่มี providers เลย → fallback ไปอ่าน data/llm_fallback.yaml (backward compat)
"""

import os
import json
import time

from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase
from core.utils import llm as llm_factory

TAG = __name__
logger = setup_logging()

DEFAULT_CONFIG_PATH = "/opt/xiaozhi-esp32-server/data/llm_fallback.yaml"
DEFAULT_COOLDOWN = 300
ALL_DOWN_MSG = "ขออภัยค่ะ ระบบผู้ช่วยขัดข้องชั่วคราว รบกวนลองใหม่อีกครั้งนะคะ"

# provider type ที่ไม่ต้องใช้ api_key (local)
NO_KEY_TYPES = {"ollama", "xinference"}
# ค่าที่ถือว่าเป็น placeholder (ยังไม่ได้ตั้ง key จริง)
PLACEHOLDER_HINTS = ("your_", "placeholder", "changeme", "xxxx", "<", "ใส่", "เติม", "todo")
# ลำดับ field เมื่อ parse แบบ delimited
DELIM_KEYS = ["label", "type", "model_name", "base_url", "api_key", "max_tokens"]


def _is_placeholder_key(key, ptype):
    # มีค่า key: ถ้าเป็น placeholder (YOUR_.../ใส่.../<...>) → ข้ามเสมอ ไม่ว่า type ไหน
    if key is not None and str(key).strip():
        k = str(key).strip().lower()
        return any(h in k for h in PLACEHOLDER_HINTS)
    # key ว่าง: local type (ollama/xinference) ไม่ต้องมี key → ไม่ข้าม; type อื่น → ข้าม
    return ptype not in NO_KEY_TYPES


def _parse_providers(raw):
    """แปลง config.providers (list / JSON string / delimited string) → list[dict]"""
    if isinstance(raw, list):
        return [dict(x) for x in raw if isinstance(x, dict)]
    if not isinstance(raw, str) or not raw.strip():
        return []
    s = raw.strip()
    # 1) ลอง JSON array ก่อน
    try:
        v = json.loads(s)
        if isinstance(v, list):
            return [dict(x) for x in v if isinstance(x, dict)]
    except Exception:
        pass
    # 2) delimited: บรรทัดละชั้น (รองรับ ;; เป็นตัวคั่นชั้นด้วย), field คั่น |
    out = []
    for line in s.replace(";;", "\n").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        d = {}
        for i, val in enumerate(parts):
            if i < len(DELIM_KEYS) and val != "":
                d[DELIM_KEYS[i]] = val
        if d:
            out.append(d)
    return out


def _load_yaml(path):
    try:
        if path and os.path.exists(path):
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return data
    except Exception as e:
        logger.bind(tag=TAG).error(f"[fallback] อ่าน {path} ไม่ได้: {e}")
    return {}


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        config = config or {}
        providers_cfg = _parse_providers(config.get("providers"))
        cooldown = config.get("cooldown_seconds")

        # ไม่มี providers ใน config → อ่านจาก yaml (backward compat)
        if not providers_cfg:
            y = _load_yaml(config.get("config_file") or DEFAULT_CONFIG_PATH)
            providers_cfg = _parse_providers(y.get("providers"))
            if cooldown in (None, ""):
                cooldown = y.get("cooldown_seconds")

        try:
            self.cooldown = int(cooldown) if cooldown not in (None, "") else DEFAULT_COOLDOWN
        except (ValueError, TypeError):
            self.cooldown = DEFAULT_COOLDOWN

        self._chain = []
        skipped = []
        for idx, sub in enumerate(providers_cfg):
            sub = dict(sub)
            sub_type = (sub.get("type") or "openai").strip()
            label = sub.get("label") or f"{sub_type}:{sub.get('model_name')}"
            # ข้ามชั้นที่ยังไม่ใส่ key จริง
            if _is_placeholder_key(sub.get("api_key"), sub_type):
                skipped.append(label)
                continue
            # normalize: max_tokens เป็น int ถ้ากรอกมาเป็น string
            if isinstance(sub.get("max_tokens"), str) and sub["max_tokens"].isdigit():
                sub["max_tokens"] = int(sub["max_tokens"])
            try:
                inst = llm_factory.create_instance(sub_type, sub)
                # fail-fast: ปิด auto-retry ของ openai client (default 2 + backoff)
                # + timeout สั้นลง → เจอ error/ช้า เลื่อนชั้นถัดไปเร็ว ไม่หน่วงทั้ง chain
                client = getattr(inst, "client", None)
                if client is not None and hasattr(client, "with_options"):
                    try:
                        inst.client = client.with_options(max_retries=0, timeout=30.0)
                    except Exception:
                        pass
                self._chain.append({"label": label, "provider": inst, "cool_until": 0.0})
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"[fallback] init ชั้น '{label}' ล้มเหลว ข้ามไป: {type(e).__name__}: {e}"
                )

        if skipped:
            logger.bind(tag=TAG).warning(
                f"[fallback] ข้ามชั้นที่ยังไม่ได้ตั้ง key: {skipped} (เติม key ใน WebUI แล้วจะใช้งานได้)"
            )
        if not self._chain:
            raise ValueError(
                "[fallback] ไม่มี sub-provider ที่ใช้งานได้เลย — ตรวจ providers/keys ใน WebUI หรือ data/llm_fallback.yaml"
            )
        logger.bind(tag=TAG).info(
            f"[fallback] พร้อมใช้งาน chain={[c['label'] for c in self._chain]} cooldown={self.cooldown}s"
        )

    def _order(self):
        now = time.monotonic()
        fresh = [c for c in self._chain if c["cool_until"] <= now]
        return fresh if fresh else self._chain

    def _trip(self, entry, err):
        entry["cool_until"] = time.monotonic() + self.cooldown
        logger.bind(tag=TAG).warning(
            f"[fallback] '{entry['label']}' ใช้ไม่ได้ ({type(err).__name__}: {str(err)[:160]}); "
            f"พัก {self.cooldown}s แล้วเลื่อนไปชั้นถัดไป"
        )

    def response(self, session_id, dialogue, **kwargs):
        last_err = None
        for entry in self._order():
            started = False
            try:
                for token in entry["provider"].response(session_id, dialogue, **kwargs):
                    started = True
                    yield token
                return
            except Exception as e:
                last_err = e
                if started:
                    logger.bind(tag=TAG).error(
                        f"[fallback] '{entry['label']}' หลุดกลางสตรีม: {type(e).__name__}: {e}"
                    )
                    return
                self._trip(entry, e)
        logger.bind(tag=TAG).error(f"[fallback] ทุกชั้นใช้ไม่ได้ error สุดท้าย: {last_err}")
        yield ALL_DOWN_MSG

    def response_with_functions(self, session_id, dialogue, functions=None, **kwargs):
        last_err = None
        for entry in self._order():
            started = False
            try:
                for item in entry["provider"].response_with_functions(
                    session_id, dialogue, functions=functions, **kwargs
                ):
                    started = True
                    yield item
                return
            except Exception as e:
                last_err = e
                if started:
                    logger.bind(tag=TAG).error(
                        f"[fallback] '{entry['label']}' (fc) หลุดกลางสตรีม: {type(e).__name__}: {e}"
                    )
                    return
                self._trip(entry, e)
        logger.bind(tag=TAG).error(f"[fallback] (fc) ทุกชั้นใช้ไม่ได้ error สุดท้าย: {last_err}")
        yield ALL_DOWN_MSG, None
