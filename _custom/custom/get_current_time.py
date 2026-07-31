"""
get_current_time — เวลาปัจจุบันแบบสด อ่านจากนาฬิกาเซิร์ฟเวอร์ (sync กับ NTP อยู่แล้ว)

ทำไมต้องมี ทั้งที่ Context Provider ก็ฉีดเวลาให้แล้ว:
  Context ถูกดึง "ครั้งเดียวตอนปลุก" แล้วค้างอยู่ใน system prompt ทั้ง session
  คุยไป 5 นาที เวลาใน prompt ก็ยังเป็นของ 5 นาทีที่แล้ว → ตอบช้ากว่าจริง
  ฟังก์ชันนี้ดึงสด ๆ ตอนถาม จึงตรงเสมอ (ต่างกันแค่ latency ของ TTS)

แหล่งเวลา: นาฬิการะบบของ xiaozhi-server → systemd-timesyncd (NTP) → ตรวจด้วย `timedatectl`
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

TZ = ZoneInfo("Asia/Bangkok")
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


@register_function(
    "get_current_time", GET_CURRENT_TIME_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def get_current_time(conn: "ConnectionHandler", with_seconds: bool = False):
    try:
        now = datetime.now(TZ)
        clock = now.strftime("%H:%M:%S") if with_seconds else now.strftime("%H:%M")
        date_th = (
            f"วัน{TH_DAYS[now.weekday()]}ที่ {now.day} "
            f"{TH_MONTHS[now.month - 1]} พ.ศ. {now.year + 543}"
        )
        text = (
            f"เวลาปัจจุบัน {clock} น. ({date_th}) เขตเวลา Asia/Bangkok "
            f"อ้างอิงนาฬิกาเซิร์ฟเวอร์ที่ sync กับ NTP\n"
            f"(ตอบสั้น ๆ เป็นภาษาพูด ไม่ต้องอ่านคำว่า Asia/Bangkok หรือ NTP ออกเสียง "
            f"เว้นแต่ผู้ใช้ถามถึงแหล่งเวลาโดยตรง)"
        )
        logger.bind(tag=TAG).info(f"get_current_time → {clock}")
        return ActionResponse(Action.REQLLM, text, None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"get_current_time ผิดพลาด: {e}")
        return ActionResponse(Action.RESPONSE, None, "ตอนนี้ดูเวลาไม่ได้ค่ะ")
