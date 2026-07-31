"""
get_current_time — เวลาปัจจุบันแบบสด อ่านจากนาฬิกาเซิร์ฟเวอร์ (sync กับ NTP อยู่แล้ว)

ทำไมต้องมี ทั้งที่ Context Provider ก็ฉีดเวลาให้แล้ว:
  Context ถูกดึง "ครั้งเดียวตอนปลุก" แล้วค้างอยู่ใน system prompt ทั้ง session
  คุยไป 5 นาที เวลาใน prompt ก็ยังเป็นของ 5 นาทีที่แล้ว → ตอบช้ากว่าจริง
  ฟังก์ชันนี้ดึงสด ๆ ตอนถาม จึงตรงเสมอ (ต่างกันแค่ latency ของ TTS)

แหล่งเวลา: นาฬิการะบบของ xiaozhi-server → systemd-timesyncd (NTP) → ตรวจด้วย `timedatectl`
"""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

DEFAULT_TIMEZONE = "Asia/Bangkok"
DEFAULT_TIMEZONE_OFFSET = 7  # ใช้เมื่อระบบไม่มีฐานข้อมูล tz (tzdata)

TH_DAYS = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
TH_MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
             "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]

GET_CURRENT_TIME_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_current_time",
        "description": (
            "ดึงเวลาปัจจุบันแบบสดจากนาฬิกาที่ sync กับ NTP server "
            "ใช้เมื่อผู้ใช้ถามเวลา วันที่ หรือขอความละเอียดระดับวินาที "
            "หรือเมื่อผู้ใช้สงสัยว่าเวลาที่บอกไปคลาดเคลื่อน "
            "ข้อมูลจากฟังก์ชันนี้แม่นยำกว่าเวลาที่อยู่ใน context เสมอ"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "with_seconds": {
                    "type": "boolean",
                    "description": "true ถ้าผู้ใช้ขอวินาทีด้วย (ค่าเริ่มต้น false)",
                }
            },
            "required": [],
        },
    },
}


def _resolve_timezone(conn: "ConnectionHandler"):
    """เขตเวลาจาก plugins.get_current_time.timezone ถ้าไม่มีใช้ Asia/Bangkok
    และถ้าเครื่องไม่มี tzdata จะถอยไปใช้ offset คงที่จาก server.timezone_offset"""
    config = getattr(conn, "config", None) or {}

    plugin_config = config.get("plugins", {}).get("get_current_time", {})
    # manager-api may deliver plugin params as a JSON string instead of a dict
    if isinstance(plugin_config, str):
        try:
            plugin_config = json.loads(plugin_config)
        except ValueError:
            plugin_config = {}
    tz_name = plugin_config.get("timezone") or DEFAULT_TIMEZONE

    try:
        return ZoneInfo(tz_name), tz_name
    except (ZoneInfoNotFoundError, ValueError) as e:
        offset = config.get("server", {}).get(
            "timezone_offset", DEFAULT_TIMEZONE_OFFSET
        )
        try:
            offset = float(offset)
        except (TypeError, ValueError):
            offset = DEFAULT_TIMEZONE_OFFSET
        logger.bind(tag=TAG).warning(
            f"ไม่รู้จักเขตเวลา '{tz_name}' ({e}) ใช้ offset UTC{offset:+g} แทน"
        )
        return timezone(timedelta(hours=offset)), f"UTC{offset:+g}"


@register_function(
    "get_current_time", GET_CURRENT_TIME_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def get_current_time(conn: "ConnectionHandler", with_seconds: bool = False):
    try:
        tz, tz_name = _resolve_timezone(conn)
        now = datetime.now(tz)
        clock = now.strftime("%H:%M:%S") if with_seconds else now.strftime("%H:%M")
        date_th = (
            f"วัน{TH_DAYS[now.weekday()]}ที่ {now.day} "
            f"{TH_MONTHS[now.month - 1]} พ.ศ. {now.year + 543}"
        )
        text = (
            f"เวลาปัจจุบัน {clock} น. ({date_th}) เขตเวลา {tz_name} "
            f"อ้างอิงนาฬิกาเซิร์ฟเวอร์ที่ sync กับ NTP\n"
            f"(ตอบสั้น ๆ เป็นภาษาพูด ไม่ต้องอ่านชื่อเขตเวลาหรือคำว่า NTP ออกเสียง "
            f"เว้นแต่ผู้ใช้ถามถึงแหล่งเวลาโดยตรง)"
        )
        logger.bind(tag=TAG).info(f"get_current_time → {clock}")
        return ActionResponse(Action.REQLLM, text, None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"get_current_time ผิดพลาด: {e}")
        return ActionResponse(Action.RESPONSE, None, "ตอนนี้ดูเวลาไม่ได้ค่ะ")
