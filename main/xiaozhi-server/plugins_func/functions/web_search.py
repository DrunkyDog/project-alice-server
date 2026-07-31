# Web search plugin (Thai-first) — provider fallback chain:
#   1. Tavily            (plugins.web_search.api_key, tvly-...) — มี answer สรุปมาให้เลย
#   2. Brave Search API  (plugins.web_search.brave_api_key)     — free tier 2,000 ครั้ง/เดือน
# ตั้ง provider เป็น auto (ค่าเริ่มต้น) เพื่อไล่ตามลำดับข้างบน หรือระบุชื่อ provider ตรง ๆ ก็ได้
import json
import re
import httpx
from config.logger import setup_logging
from plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

_DEFAULT_DESCRIPTION = (
    "เครื่องมือค้นหาข้อมูลบนอินเทอร์เน็ต ใช้เมื่อผู้ใช้ถามเรื่องที่ต้องรู้ข้อมูลล่าสุด "
    "หรือข้อมูลที่ไม่มีในความรู้ของโมเดล เช่น ราคา ผลกีฬา เหตุการณ์ปัจจุบัน "
    "ข้อมูลเฉพาะเจาะจงของบุคคล สถานที่ หรือสินค้า "
    "อย่าใช้กับคำถามเรื่องเวลา สภาพอากาศ หรือข่าว เพราะมีเครื่องมือเฉพาะอยู่แล้ว"
)

WEB_SEARCH_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": _DEFAULT_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "คำค้นหรือคำถาม ใช้ภาษาเดียวกับที่ผู้ใช้ถาม "
                        "(ถามไทยให้ค้นไทย) ถ้าเป็นเรื่องต่างประเทศจะค้นเป็นภาษาอังกฤษก็ได้"
                    ),
                }
            },
            "required": ["query"],
        },
    },
}

TIMEOUT = httpx.Timeout(15.0, connect=3.0)

PROVIDERS = ("tavily", "brave")

# Tavily รับชื่อประเทศแบบเต็มตัวพิมพ์เล็ก ไม่ใช่รหัส ISO 2 ตัว
_TAVILY_COUNTRY = {
    "TH": "thailand",
    "US": "united states",
    "GB": "united kingdom",
    "SG": "singapore",
    "JP": "japan",
    "CN": "china",
}


def _clean(text):
    """ล้าง markup ก่อนส่งเข้า LLM/TTS
    - Brave ใส่ <strong> ครอบคำที่แมตช์
    - Tavily แปลงหน้าเว็บเป็น markdown ทำให้บางหน้า (เช่น ตารางราคา) เหลือแต่ซาก | และ ---
    """
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", str(text))
    text = re.sub(r"\|[\s|:-]*", " ", text)  # ซากตาราง markdown
    text = re.sub(r"-{3,}", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _auth_error(status_code):
    if status_code in (401, 403):
        return "API key ของบริการค้นหาไม่ถูกต้องหรือหมดอายุ"
    if status_code == 429:
        return "โควตาการค้นหาหมดแล้ว"
    return None


# ---------- Tavily (tier 1) ----------


async def _search_tavily(api_key, query, max_results, country):
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": "advanced",
    }
    tavily_country = _TAVILY_COUNTRY.get((country or "").upper())
    if tavily_country:
        # topic ต้องเป็น general ถึงจะใช้ country ได้
        payload["topic"] = "general"
        payload["country"] = tavily_country

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(url, json=payload, headers=headers)
        # ถ้า API ไม่รู้จักพารามิเตอร์ localization ให้ยิงซ้ำแบบพื้นฐาน
        if response.status_code in (400, 422) and tavily_country:
            logger.bind(tag=TAG).warning(
                f"Tavily ปฏิเสธพารามิเตอร์ country ({response.status_code}) ลองใหม่แบบไม่ระบุประเทศ"
            )
            payload.pop("country", None)
            payload.pop("topic", None)
            response = await client.post(url, json=payload, headers=headers)

    response.raise_for_status()
    data = response.json()

    items = []
    for item in data.get("results", []):
        items.append({
            "title": _clean(item.get("title", "")),
            "snippet": _clean(item.get("content", "")),
            "date": item.get("published_date", ""),
        })
    return _clean(data.get("answer", "")), items


# ---------- Brave Search (tier 2) ----------


async def _search_brave(api_key, query, max_results, country, lang):
    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }
    params = {
        "q": query,
        "count": max_results,
        "country": (country or "TH").upper(),
        "search_lang": lang or "th",
        "spellcheck": 1,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()

    items = []
    for item in data.get("web", {}).get("results", []):
        items.append({
            "title": _clean(item.get("title", "")),
            "snippet": _clean(item.get("description", "")),
            "date": item.get("age", ""),
        })
    return "", items


def _format_report(query, answer, items, max_chars):
    """ประกอบผลลัพธ์เป็นข้อความป้อนกลับเข้า LLM (ไม่ใส่ URL เพราะข้อความจะถูกอ่านออกเสียง)"""
    lines = [f"# ผลการค้นเว็บ เกี่ยวกับ「{query}」"]
    if answer:
        lines.append(f"\nสรุป: {answer}")

    used = len(answer)
    shown = 0
    entries = []
    for item in items:
        if used >= max_chars:
            break
        snippet = item["snippet"][: max(0, max_chars - used)]
        if not item["title"] and not snippet:
            continue
        entry = f"{shown + 1}. {item['title'] or 'ไม่มีหัวข้อ'}"
        if item["date"]:
            entry += f" ({item['date']})"
        if snippet:
            entry += f"\n   {snippet}"
        entries.append(entry)
        shown += 1
        used += len(snippet)

    if not answer and shown == 0:
        return None

    if entries:
        lines.append("\nข้อมูลที่พบ:")
        lines.extend(entries)

    lines.append(
        "\n(สรุปเป็นภาษาพูดสั้น ๆ ตอบเฉพาะที่ผู้ใช้ถาม เพราะข้อความนี้จะถูกอ่านออกเสียง "
        "ห้ามอ่าน URL ชื่อเว็บ หรือสัญลักษณ์ markdown ออกเสียง "
        "ถ้าข้อมูลขัดแย้งกันให้บอกว่าข้อมูลยังไม่ตรงกัน)"
    )
    return "\n".join(lines)


@register_function("web_search", WEB_SEARCH_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def web_search(conn: "ConnectionHandler", query: str = None):
    logger.bind(tag=TAG).info(f"web_search called | query={query}")
    if not query or not isinstance(query, str):
        return ActionResponse(
            Action.REQLLM, "ไม่ได้รับคำค้น ให้ถามผู้ใช้ว่าต้องการค้นเรื่องอะไร", None
        )

    config = conn.config.get("plugins", {}).get("web_search", {})
    # manager-api may deliver plugin params as a JSON string instead of a dict
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except ValueError:
            config = {}

    provider = str(config.get("provider", "auto")).lower().strip() or "auto"
    try:
        max_results = int(config.get("max_results", 5))
    except (TypeError, ValueError):
        max_results = 5
    try:
        max_chars = int(config.get("max_chars", 1500))
    except (TypeError, ValueError):
        max_chars = 1500
    country = str(config.get("country") or "TH")
    lang = str(config.get("lang") or "th")

    # api_key คือคีย์ Tavily (ชื่อเดิม) รองรับชื่อใหม่ tavily_api_key ด้วย
    keys = {
        "tavily": str(config.get("tavily_api_key") or config.get("api_key") or "").strip(),
        "brave": str(config.get("brave_api_key") or "").strip(),
    }

    if provider == "auto":
        order = [p for p in PROVIDERS if keys[p]]
    elif provider in PROVIDERS:
        order = [provider] if keys[provider] else []
    else:
        return ActionResponse(
            Action.REQLLM,
            f"ตั้งค่าแหล่งค้นหาไม่ถูกต้อง (provider={provider}) "
            f"รองรับเฉพาะ {', '.join(PROVIDERS)} หรือ auto",
            None,
        )

    if not order:
        return ActionResponse(
            Action.REQLLM,
            "ยังไม่ได้ตั้ง API key ของบริการค้นหา ให้บอกผู้ใช้ว่าตอนนี้ยังค้นเว็บไม่ได้",
            None,
        )

    logger.bind(tag=TAG).info(
        f"web_search config | provider={provider} | ลำดับที่จะใช้={order} "
        f"| max_results={max_results} | country={country} | lang={lang}"
    )

    last_error = "ไม่พบข้อมูลที่เกี่ยวข้อง"
    for name in order:
        try:
            if name == "tavily":
                answer, items = await _search_tavily(
                    keys[name], query, max_results, country
                )
            else:
                answer, items = await _search_brave(
                    keys[name], query, max_results, country, lang
                )

            report = _format_report(query, answer, items, max_chars)
            if report is None:
                logger.bind(tag=TAG).info(f"{name}: ไม่พบผลลัพธ์ q={query[:40]}")
                last_error = "ไม่พบข้อมูลที่เกี่ยวข้อง"
                continue

            logger.bind(tag=TAG).info(
                f"web_search สำเร็จ | provider={name} | ผลลัพธ์ {len(items)} รายการ"
            )
            return ActionResponse(Action.REQLLM, report, None)

        except httpx.TimeoutException:
            logger.bind(tag=TAG).error(f"{name}: ค้นหาหมดเวลา")
            last_error = "การค้นหาใช้เวลานานเกินไป"
        except httpx.HTTPStatusError as e:
            detail = _auth_error(e.response.status_code)
            logger.bind(tag=TAG).error(
                f"{name}: ค้นหาไม่สำเร็จ status={e.response.status_code} {detail or ''}"
            )
            last_error = detail or f"บริการค้นหาตอบกลับผิดพลาด ({e.response.status_code})"
        except Exception as e:
            logger.bind(tag=TAG).error(f"{name}: ค้นหาผิดพลาด {type(e).__name__}: {e}")
            last_error = "เกิดข้อผิดพลาดระหว่างค้นหา"

    return ActionResponse(
        Action.REQLLM,
        f"ค้นเว็บไม่สำเร็จ ({last_error}) ให้บอกผู้ใช้สั้น ๆ แล้วตอบจากความรู้ทั่วไปถ้าตอบได้",
        None,
    )
