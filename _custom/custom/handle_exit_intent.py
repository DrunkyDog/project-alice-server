"""
handle_exit_intent — เวอร์ชันไทย (override ของเดิมที่เป็นภาษาจีน)

ทำไมต้อง override:
  ปลั๊กอินนี้คืน Action.RESPONSE = พูดข้อความ say_goodbye ออกลำโพงตรง ๆ
  **ไม่ผ่าน LLM หลัก** → กฎ [LANGUAGE RULE] ในระบบ prompt ไม่มีผล
  intent LLM (prompt ภาษาจีน) จึงสร้างคำอำลาเป็นจีน แล้วถูกพูดออกมาดิบ ๆ

วิธีแก้: กรองที่ปลายทาง — ถ้าข้อความมีอักษรจีน/ญี่ปุ่น/เกาหลี ทิ้งแล้วใช้คำอำลาไทยแทน
"""
import re
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# ช่วงอักขระ CJK: จีน, ฮิรางานะ, คาตากานะ, ฮันกึล
CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿가-힯]")
THAI = re.compile(r"[฀-๿]")

DEFAULT_GOODBYE = "บายค่ะ เรียกนุ้งได้ตลอดนะ"

handle_exit_intent_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_exit_intent",
        "description": (
            "เรียกเมื่อผู้ใช้ต้องการจบบทสนทนาหรือออกจากระบบ "
            "เช่น บาย, ไว้เจอกันใหม่, พอแค่นี้, จบแล้ว, ok แค่นี้แหละ"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "say_goodbye": {
                    "type": "string",
                    "description": (
                        "คำอำลาสั้น ๆ **ต้องเป็นภาษาไทยเท่านั้น** ห้ามภาษาจีนหรืออังกฤษเด็ดขาด "
                        "ตัวอย่าง: บายค่ะ เรียกนุ้งได้ตลอดนะ"
                    ),
                }
            },
            "required": ["say_goodbye"],
        },
    },
}


def _sanitize(text: str | None) -> str:
    """คืนคำอำลาไทยเสมอ — ถ้าอันที่ได้มาไม่ใช่ไทย ใช้ค่า default"""
    if not text or not text.strip():
        return DEFAULT_GOODBYE
    text = text.strip()
    if CJK.search(text):
        logger.bind(tag=TAG).warning(f"คำอำลาเป็นภาษา CJK ถูกแทนที่: {text[:40]}")
        return DEFAULT_GOODBYE
    if not THAI.search(text):
        logger.bind(tag=TAG).warning(f"คำอำลาไม่มีอักษรไทย ถูกแทนที่: {text[:40]}")
        return DEFAULT_GOODBYE
    return text


@register_function(
    "handle_exit_intent", handle_exit_intent_function_desc, ToolType.SYSTEM_CTL
)
def handle_exit_intent(conn: "ConnectionHandler", say_goodbye: str | None = None):
    try:
        say_goodbye = _sanitize(say_goodbye)
        if not conn.close_after_chat:
            conn.close_after_chat = True
        logger.bind(tag=TAG).info(f"ปิดบทสนทนา: {say_goodbye}")
        return ActionResponse(
            action=Action.RESPONSE, result="exit intent handled", response=say_goodbye
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"handle_exit_intent ผิดพลาด: {e}")
        return ActionResponse(action=Action.NONE, result="exit intent failed", response="")
