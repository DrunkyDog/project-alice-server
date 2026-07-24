import random
import httpx
from io import BytesIO
from markitdown import MarkItDown, StreamInfo
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler


TAG = __name__
logger = setup_logging()

CHANNEL_MAP = {
    "V2EX": "v2ex-share",
    "Zhihu": "zhihu",
    "Weibo": "weibo",
    "Lianhe Zaobao": "zaobao",
    "Coolapk": "coolapk",
    "MKTNews": "mktnews-flash",
    "Wall Street Journal": "wallstreetcn-quick",
    "36Kr": "36kr-quick",
    "Douyin": "douyin",
    "Hupu": "hupu",
    "Baidu Tieba": "tieba",
    "Toutiao": "toutiao",
    "IT Home": "ithome",
    "The Paper": "thepaper",
    "Sputnik News": "sputniknewscn",
    "Reference News": "cankaoxiaoxi",
    "Pcbeta": "pcbeta-windows11",
    "Caixin": "cls-depth",
    "Xueqiu": "xueqiu-hotstock",
    "Gelonghui": "gelonghui",
    "Fast Bull": "fastbull-express",
    "Solidot": "solidot",
    "Hacker News": "hackernews",
    "Product Hunt": "producthunt",
    "Github": "github-trending-today",
    "Bilibili": "bilibili-hot-search",
    "Kuaishou": "kuaishou",
    "Kaopu News": "kaopu",
    "Jin10": "jin10",
    "Baidu Hot Search": "baidu",
    "Nowcoder": "nowcoder",
    "Sspai": "sspai",
    "Juejin": "juejin",
    "Ifeng": "ifeng",
    "Chongbuluo": "chongbuluo-latest",
}

# Default news source dictionary used when no configuration is specified
DEFAULT_NEWS_SOURCES = "The Paper;Baidu Hot Search;Caixin"

def _get_newsnow_config(conn):
    # Read from the connection configuration
    plugins = conn.config.get("plugins", {})
    newsnow = plugins.get("get_news_from_newsnow", {})
    sources = newsnow.get("news_sources", "")
    if isinstance(sources, str) and sources.strip():
        return sources

    return ""

def get_news_sources_from_config(conn):
    """Read the news source string from configuration"""
    try:
        result = _get_newsnow_config(conn)
        if result:
            logger.bind(tag=TAG).debug(f"Using the configured news source: {result}")
            return result

        logger.bind(tag=TAG).debug("No news source configuration found; using the default configuration")
        return DEFAULT_NEWS_SOURCES

    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to read the news source configuration: {e}; using the default configuration")
        return DEFAULT_NEWS_SOURCES


# Get the available news source names from the default configuration (resolved at runtime by get_news_sources_from_config)
example_sources_str = DEFAULT_NEWS_SOURCES.replace(";", ", ")

GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_newsnow",
        "description": "Called when the user asks to view or listen to the news (for example, 'Give me some news' or 'What news do we have today?').",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": f"The standard source name, such as {example_sources_str}. Optional; if omitted, the default source is used",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Whether to fetch detailed content. Defaults to false. If true, it retrieves the details of the most recent news item",
                },
                "lang": {
                    "type": "string",
                    "description": "The user's language code, such as zh_CN, zh_HK, en_US, or ja_JP. Defaults to zh_CN",
                },
            },
            "required": ["lang"],
        },
    },
}


async def fetch_news_from_api(conn: "ConnectionHandler", source="thepaper"):
    """Fetch the list of news from the API"""
    try:
        api_url = f"https://newsnow.busiyi.world/api/s?id={source}"

        news_config = conn.config.get("plugins", {}).get("get_news_from_newsnow", {})
        if news_config.get("url"):
            api_url = news_config["url"] + source

        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            response = await client.get(api_url, headers=headers)

        data = response.json()

        if "items" in data:
            return data["items"]
        else:
            logger.bind(tag=TAG).error(f"The news API returned an unexpected response format: {data}")
            return []

    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch news from the API: {e}")
        return []


async def fetch_news_detail(url):
    """Fetch the news detail page content and clean the HTML using MarkItDown"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            response = await client.get(url, headers=headers)

        # Use MarkItDown to clean the HTML content
        md = MarkItDown(enable_plugins=False)
        result = md.convert_stream(
            BytesIO(response.content),
            stream_info=StreamInfo(
                mimetype="text/html",
                extension=".html",
                charset=response.encoding or "utf-8",
            ),
        )

        # Retrieve the cleaned text content
        clean_text = result.text_content

        # If the cleaned content is empty, return a helpful message
        if not clean_text or len(clean_text.strip()) == 0:
            logger.bind(tag=TAG).warning(f"The cleaned news content was empty: {url}")
            return "Unable to parse the news detail content; the site structure may be unusual or the content may be restricted."

        return clean_text
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch the news detail: {e}")
        return "Unable to retrieve detailed content"


@register_function(
    "get_news_from_newsnow",
    GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
async def get_news_from_newsnow(
    conn: "ConnectionHandler",
    source: str = "The Paper",
    detail: bool = False,
    lang: str = "zh_CN",
):
    """Fetch news, pick one at random for broadcast, or retrieve the details of the previous news item"""
    try:
        # Read the currently configured news source
        news_sources = get_news_sources_from_config(conn)

        # If detail is true, retrieve the details of the previous news item
        detail = str(detail).lower() == "true"
        if detail:
            if (
                not hasattr(conn, "last_newsnow_link")
                or not conn.last_newsnow_link
                or "url" not in conn.last_newsnow_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, I could not find the most recent news query. Please fetch a news item first.",
                    None,
                )

            url = conn.last_newsnow_link.get("url")
            title = conn.last_newsnow_link.get("title", "Unknown title")
            source_id = conn.last_newsnow_link.get("source_id", "thepaper")
            source_name = CHANNEL_MAP.get(source_id, "Unknown source")

            if not url or url == "#":
                return ActionResponse(
                    Action.REQLLM, "Sorry, that news item does not have a usable link for detailed content.", None
                )

            logger.bind(tag=TAG).debug(
                f"Fetching news details: {title}, source: {source_name}, URL={url}"
            )

            # Fetch the news details
            detail_content = await fetch_news_detail(url)

            if not detail_content or detail_content == "Unable to retrieve detailed content":
                return ActionResponse(
                    Action.REQLLM,
                    f"Sorry, I was unable to retrieve the detailed content for \"{title}\"; the link may be invalid or the site structure may have changed.",
                    None,
                )

            # Build the detail report
            detail_report = (
                f"Based on the following data, respond to the user's news detail request in {lang}:\n\n"
                f"News title: {title}\n"
                # f"News source: {source_name}\n"
                f"Detailed content: {detail_content}\n\n"
                f"(Please summarize the above news content, extract the key information, and present it naturally and fluently to the user,"
                f"without mentioning that it is a summary, as if you were narrating a complete news story)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Otherwise, fetch the news list and pick one at random
        # Convert the Chinese source name to an English ID
        english_source_id = None

        # Check whether the provided Chinese source name exists in the configured sources
        news_sources_list = [
            name.strip() for name in news_sources.split(";") if name.strip()
        ]
        if source in news_sources_list:
            # If the provided Chinese source name exists in the configured sources, look up the corresponding English ID in CHANNEL_MAP
            english_source_id = CHANNEL_MAP.get(source)

        # If no matching English ID is found, use the default source
        if not english_source_id:
            logger.bind(tag=TAG).warning(f"Invalid news source: {source}; using the default source The Paper")
            english_source_id = "thepaper"
            source = "The Paper"

        logger.bind(tag=TAG).info(f"Fetching news: source={source}({english_source_id})")

        # Fetch the news list
        news_items = await fetch_news_from_api(conn, english_source_id)

        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                f"Sorry, I could not retrieve news information from {source}. Please try again later or choose another news source.",
                None,
            )

        # Randomly select a news item
        selected_news = random.choice(news_items)

        # Save the current news link to the connection object so it can be queried later for details
        if not hasattr(conn, "last_newsnow_link"):
            conn.last_newsnow_link = {}
        conn.last_newsnow_link = {
            "url": selected_news.get("url", "#"),
            "title": selected_news.get("title", "Unknown title"),
            "source_id": english_source_id,
        }

        # Build the news report
        news_report = (
            f"Based on the following data, respond to the user's news query in {lang}:\n\n"
            f"News title: {selected_news['title']}\n"
            # f"News source: {source}\n"
            f"(Please announce this news title naturally and fluently to the user,"
            f"and let them know they can ask for detailed content, which will retrieve the full article details.)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"An error occurred while fetching news: {e}")
        return ActionResponse(
            Action.REQLLM, "Sorry, an error occurred while fetching the news. Please try again later.", None
        )
