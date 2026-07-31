import random
import re
import requests
import xml.etree.ElementTree as ET
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

HEADERS = {"User-Agent": "Mozilla/5.0 (xiaozhi-esp32-server thai-news)"}

GET_NEWS_FROM_THAI_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_thai",
        "description": (
            "เรียกเมื่อผู้ใช้อยากฟังข่าวไทย เช่น 'ขอข่าวหน่อย' 'วันนี้มีข่าวอะไร' "
            "'ข่าวเศรษฐกิจ' 'ข่าวกีฬา' ผู้ใช้ระบุหมวดได้ เช่น ทั่วไป เศรษฐกิจ "
            "ต่างประเทศ กีฬา บันเทิง ในประเทศ เทคโนโลยี ถ้าไม่ระบุจะอ่านข่าวทั่วไป"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": (
                        "หมวดข่าว เช่น ทั่วไป/เศรษฐกิจ/ต่างประเทศ/กีฬา/บันเทิง/"
                        "ในประเทศ/เทคโนโลยี เป็นพารามิเตอร์ทางเลือก ไม่ใส่ก็ได้"
                    ),
                },
                "detail": {
                    "type": "boolean",
                    "description": "ขอรายละเอียดข่าวก่อนหน้าหรือไม่ ค่าเริ่มต้น false",
                },
                "lang": {
                    "type": "string",
                    "description": "language code ของผู้ใช้ เช่น th_TH/en_US ค่าเริ่มต้น th_TH",
                },
            },
            "required": ["lang"],
        },
    },
}

# แม็ปคำที่ผู้ใช้พูด -> key ของ config (RSS url)
CATEGORY_MAP = {
    "ทั่วไป": "default_rss_url",
    "ข่าวทั่วไป": "default_rss_url",
    "ข่าวเด่น": "default_rss_url",
    "สังคม": "default_rss_url",
    "เศรษฐกิจ": "economy_rss_url",
    "ข่าวเศรษฐกิจ": "economy_rss_url",
    "การเงิน": "economy_rss_url",
    "ธุรกิจ": "economy_rss_url",
    "ต่างประเทศ": "world_rss_url",
    "ข่าวต่างประเทศ": "world_rss_url",
    "โลก": "world_rss_url",
    "กีฬา": "sport_rss_url",
    "ข่าวกีฬา": "sport_rss_url",
    "บันเทิง": "entertain_rss_url",
    "ข่าวบันเทิง": "entertain_rss_url",
    "ดารา": "entertain_rss_url",
    "ในประเทศ": "local_rss_url",
    "ท้องถิ่น": "local_rss_url",
    "ภูมิภาค": "local_rss_url",
    "เทคโนโลยี": "tech_rss_url",
    "ข่าวไอที": "tech_rss_url",
    "ไอที": "tech_rss_url",
    "เทค": "tech_rss_url",
}

# ค่า RSS เริ่มต้น (ยืนยันใช้งานได้จริง ก.ค. 2026) เผื่อ config ไม่ได้ตั้งไว้
DEFAULT_RSS = {
    "default_rss_url": "https://www.thairath.co.th/rss/news",
    "economy_rss_url": "https://www.matichon.co.th/economy/feed",
    "world_rss_url": "https://www.matichon.co.th/foreign/feed",
    "sport_rss_url": "https://www.thairath.co.th/rss/sport",
    "entertain_rss_url": "https://www.thairath.co.th/rss/entertain",
    "local_rss_url": "https://www.matichon.co.th/local/feed",
    "tech_rss_url": "https://www.blognone.com/atom.xml",
}


def _strip_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tag(el, name):
    """หา child tag แบบไม่สน namespace (รองรับทั้ง RSS และ Atom)"""
    for child in el:
        if child.tag.split("}")[-1] == name:
            return child
    return None


def fetch_news_from_feed(url):
    """ดึงรายการข่าวจาก RSS (<item>) หรือ Atom (<entry>)"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        items = root.findall(".//{*}item")
        is_atom = False
        if not items:
            items = root.findall(".//{*}entry")
            is_atom = True

        news = []
        for it in items:
            title_el = _tag(it, "title")
            title = _strip_html(title_el.text) if title_el is not None else "ไม่มีหัวข้อ"

            if is_atom:
                link = "#"
                for c in it:
                    if c.tag.split("}")[-1] == "link" and c.get("href"):
                        link = c.get("href")
                        break
                desc_el = _tag(it, "summary") or _tag(it, "content")
                date_el = _tag(it, "updated") or _tag(it, "published")
            else:
                link_el = _tag(it, "link")
                link = link_el.text if link_el is not None and link_el.text else "#"
                desc_el = _tag(it, "description")
                date_el = _tag(it, "pubDate")

            news.append({
                "title": title,
                "link": link,
                "description": _strip_html(desc_el.text) if desc_el is not None else "",
                "pubDate": date_el.text if date_el is not None and date_el.text else "",
            })
        return news
    except Exception as e:
        logger.bind(tag=TAG).error(f"ดึง RSS ไทยไม่สำเร็จ ({url}): {e}")
        return []


def fetch_news_detail(url):
    """ดึงเนื้อหาข่าวแบบละเอียดจากหน้าเว็บ"""
    try:
        from bs4 import BeautifulSoup
        resp = requests.get(url, headers=HEADERS, timeout=12)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        node = soup.select_one(
            "article, .entry-content, .article-content, .content-detail, .detail-content"
        )
        paras = (node.find_all("p") if node else soup.find_all("p"))
        content = "\n".join(p.get_text().strip() for p in paras if p.get_text().strip())
        return content[:2000] if content else "ไม่สามารถดึงเนื้อหาได้"
    except Exception as e:
        logger.bind(tag=TAG).error(f"ดึงรายละเอียดข่าวไม่สำเร็จ: {e}")
        return "ไม่สามารถดึงเนื้อหาได้"


def _resolve_url(news_config, category):
    key = CATEGORY_MAP.get((category or "").strip()) if category else None
    if not key:
        key = "default_rss_url"
    # ลำดับความสำคัญ: config ที่ผู้ใช้ตั้ง -> ค่าเริ่มต้นในตัว
    return news_config.get(key) or DEFAULT_RSS.get(key) or DEFAULT_RSS["default_rss_url"]


@register_function(
    "get_news_from_thai", GET_NEWS_FROM_THAI_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
def get_news_from_thai(
    conn: "ConnectionHandler",
    category: str = None,
    detail: bool = False,
    lang: str = "th_TH",
):
    try:
        news_config = conn.config.get("plugins", {}).get("get_news_from_thai", {})
        if isinstance(news_config, str):
            import json
            try:
                news_config = json.loads(news_config)
            except ValueError:
                news_config = {}

        if detail:
            last = getattr(conn, "last_thai_news_link", None)
            if not last or not last.get("link") or last.get("link") == "#":
                return ActionResponse(
                    Action.REQLLM,
                    "ยังไม่มีข่าวที่ค้นล่าสุด ขอข่าวสักหัวข้อก่อนนะคะ",
                    None,
                )
            content = fetch_news_detail(last["link"])
            report = (
                f"ตอบผู้ใช้เป็นภาษา {lang} โดยสรุปเนื้อหาข่าวต่อไปนี้ให้เป็นธรรมชาติ:\n\n"
                f"หัวข้อ: {last.get('title','')}\n"
                f"เนื้อหา: {content}\n\n"
                f"(สรุปใจความสำคัญ เล่าให้ลื่นไหลเหมือนเล่าข่าว ไม่ต้องบอกว่ากำลังสรุป)"
            )
            return ActionResponse(Action.REQLLM, report, None)

        url = _resolve_url(news_config, category)
        logger.bind(tag=TAG).info(f"ข่าวไทย: หมวด={category}, url={url}")
        news = fetch_news_from_feed(url)

        # ถ้าหมวดที่เลือกดึงไม่ได้ ลองข่าวทั่วไปเป็น fallback
        if not news and url != DEFAULT_RSS["default_rss_url"]:
            news = fetch_news_from_feed(DEFAULT_RSS["default_rss_url"])

        if not news:
            return ActionResponse(
                Action.REQLLM, "ขออภัยค่ะ ดึงข่าวไม่สำเร็จ ลองใหม่อีกครั้งนะคะ", None
            )

        picked = random.choice(news)
        conn.last_thai_news_link = {"link": picked.get("link", "#"), "title": picked["title"]}

        report = (
            f"ตอบผู้ใช้เป็นภาษา {lang} โดยอ่านข่าวนี้ให้ฟังอย่างเป็นธรรมชาติ:\n\n"
            f"หัวข้อ: {picked['title']}\n"
            f"เวลา: {picked['pubDate']}\n"
            f"เนื้อหา: {picked['description']}\n"
            f"(อ่านข่าวให้ลื่นไหล สรุปได้ตามเหมาะสม ไม่ต้องมีคำเกริ่นเยิ่นเย้อ "
            f"ถ้าผู้ใช้อยากรู้เพิ่ม บอกว่าพูดว่า 'เล่าข่าวนี้ละเอียดหน่อย' ได้)"
        )
        return ActionResponse(Action.REQLLM, report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"ข่าวไทยผิดพลาด: {e}")
        return ActionResponse(
            Action.REQLLM, "ขออภัยค่ะ เกิดข้อผิดพลาดตอนดึงข่าว ลองใหม่นะคะ", None
        )
