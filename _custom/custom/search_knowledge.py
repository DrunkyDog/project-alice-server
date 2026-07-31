"""
ALICE Knowledge search — ค้นคลังความรู้ผ่าน Cloudflare Worker (alice-edge) + Vectorize
โครงสร้าง/สัญญา อ้างอิงจาก plugins_func/functions/search_from_ragflow.py
"""
import json
import requests
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

SEARCH_KNOWLEDGE_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": (
            "ค้นคลังความรู้ของโปรเจค ALICE "
            "เช่น สเปคฮาร์ดแวร์บอร์ด ESP32-S3-Touch-AMOLED-2.06 จอ แบตเตอรี่ pinout, "
            "ระบบอารมณ์ 21 แบบ, ระบบบุคลิก TARS, รายการความสามารถที่มี, โครงสร้าง Cloudflare "
            "ใช้เมื่อผู้ใช้ถามถึงรายละเอียดเฉพาะของโปรเจค อุปกรณ์ หรือการตั้งค่าที่ตอบจากความรู้ทั่วไปไม่ได้ "
            "อย่าใช้กับคำถามทั่วไป เวลา อากาศ ข่าว หรือการสั่งงานอุปกรณ์"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "คำถามที่ต้องการค้น ใช้ข้อความเต็มของผู้ใช้",
                }
            },
            "required": ["question"],
        },
    },
}


@register_function(
    "search_knowledge", SEARCH_KNOWLEDGE_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def search_knowledge(conn: "ConnectionHandler", question=None):
    cfg = conn.config.get("plugins", {}).get("search_knowledge", {})
    endpoint = cfg.get("endpoint", "")
    api_key = cfg.get("api_key", "")
    top_k = int(cfg.get("top_k", 5))
    min_score = float(cfg.get("min_score", 0.35))
    rel_ratio = float(cfg.get("rel_ratio", 0.75))
    max_chars = int(cfg.get("max_chars", 1500))

    if not question or not isinstance(question, str):
        return ActionResponse(Action.RESPONSE, None, "ไม่ได้รับคำถามที่จะค้น")
    if not endpoint:
        logger.bind(tag=TAG).error("search_knowledge: ยังไม่ได้ตั้ง endpoint ใน config")
        return ActionResponse(Action.RESPONSE, None, "ยังไม่ได้ตั้งค่าคลังความรู้")

    try:
        resp = requests.post(
            endpoint,
            json={"question": question, "top_k": top_k},
            headers={
                "x-alice-key": api_key,
                "Content-Type": "application/json",
                "User-Agent": "alice-server/1.0",  # urllib/requests UA โดน CF บล็อกได้
            },
            timeout=8,
        )
        resp.encoding = "utf-8"
        resp.raise_for_status()
        data = json.loads(resp.text)

        hits = data.get("chunks", [])
        # กรอง 2 ชั้น: ตัดคะแนนต่ำสุดแบบ absolute แล้วตัดแบบสัมพัทธ์กับผลอันดับ 1
        hits = [h for h in hits if float(h.get("score", 0)) >= min_score]
        if hits:
            top = float(hits[0].get("score", 0))
            hits = [h for h in hits if float(h.get("score", 0)) >= top * rel_ratio]

        if not hits:
            logger.bind(tag=TAG).info(f"knowledge miss q={question[:40]}")
            return ActionResponse(
                Action.REQLLM,
                "ไม่พบข้อมูลที่เกี่ยวข้องในคลังความรู้ของผู้ใช้ "
                "ให้บอกผู้ใช้สั้น ๆ ว่าไม่มีข้อมูลนี้ในคลัง แล้วตอบจากความรู้ทั่วไปถ้าตอบได้",
                None,
            )

        parts, used = [], 0
        for h in hits:
            content = str(h.get("content", "")).strip()
            if not content:
                continue
            if used + len(content) > max_chars:
                break
            parts.append(f"[{h.get('source', 'ไม่ทราบที่มา')}]\n{content}")
            used += len(content)

        context_text = (
            f"# ข้อมูลจากคลังความรู้ของผู้ใช้ เกี่ยวกับ「{question}」\n"
            + "\n\n---\n\n".join(parts)
            + "\n\n(ตอบเป็นภาษาพูดสั้น ๆ กระชับ เพราะจะถูกอ่านออกเสียง "
            "ห้ามอ่านสัญลักษณ์ markdown หรือชื่อไฟล์ออกเสียง)"
        )

        logger.bind(tag=TAG).info(
            f"knowledge hit={len(parts)} chars={used} q={question[:40]}"
        )
        return ActionResponse(Action.REQLLM, context_text, None)

    except requests.exceptions.RequestException as e:
        logger.bind(tag=TAG).error(
            f"search_knowledge เรียก Worker ล้มเหลว: {type(e).__name__}: {e}"
        )
        return ActionResponse(
            Action.RESPONSE, None, "ตอนนี้ค้นคลังความรู้ไม่ได้ ลองใหม่อีกครั้งนะ"
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"search_knowledge ผิดพลาด: {type(e).__name__}: {e}")
        return ActionResponse(
            Action.RESPONSE, None, "ค้นคลังความรู้แล้วเจอปัญหา ลองใหม่อีกครั้งนะ"
        )
