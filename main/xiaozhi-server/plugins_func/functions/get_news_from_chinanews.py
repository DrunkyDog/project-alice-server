import random
import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler


TAG = __name__
logger = setup_logging()

GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_chinanews",
        "description": (
            "Called when the user wants to view or listen to the news (for example, 'Give me some news' or 'What news is there today?')."
            "The user can specify a news category such as society news, technology news, or international news."
            "If none is specified, the default is to report society news."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "The news category, for example society, technology, or international. Optional; if not provided, the default category is used.",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Whether to retrieve detailed content. Defaults to false. If true, it retrieves the details of the previous news item.",
                },
                "lang": {
                    "type": "string",
                    "description": "The language code used by the user, for example zh_CN, zh_HK, en_US, or ja_JP. Defaults to zh_CN.",
                },
            },
            "required": ["lang"],
        },
    },
}


async def fetch_news_from_rss(rss_url):
    """Fetch a news list from an RSS source"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            response = await client.get(rss_url)

        # Parse the XML
        root = ET.fromstring(response.content)

        # Find all item elements (news entries)
        news_items = []
        for item in root.findall(".//item"):
            title = (
                item.find("title").text if item.find("title") is not None else "Untitled"
            )
            link = item.find("link").text if item.find("link") is not None else "#"
            description = (
                item.find("description").text
                if item.find("description") is not None
                else "No description"
            )
            pubDate = (
                item.find("pubDate").text
                if item.find("pubDate") is not None
                else "Unknown time"
            )

            news_items.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pubDate": pubDate,
                }
            )

        return news_items
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch RSS news: {e}")
        return []


async def fetch_news_detail(url):
    """Fetch the news detail page content and summarize it"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            response = await client.get(url)

        soup = BeautifulSoup(response.content, "html.parser")

        # Try to extract the main body content (the selector may need to be adjusted for each site)
        content_div = soup.select_one(
            ".content_desc, .content, article, .article-content"
        )
        if content_div:
            paragraphs = content_div.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content
        else:
            # If a specific content area cannot be found, try to retrieve all paragraphs
            paragraphs = soup.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content[:2000]  # Limit length
    except Exception as e:
        logger.bind(tag=TAG).error(f"Failed to fetch the news details: {e}")
        return "Unable to retrieve detailed content"


def map_category(category_text):
    """Map the user's input category to the category key used in the configuration"""
    if not category_text:
        return None

    # Category mapping dictionary; currently supports society, international, and finance news. Additional types can be added in the configuration file.
    category_map = {
        # Society news
        "society": "society_rss_url",
        "society news": "society_rss_url",
        "social": "society_rss_url",
        "social news": "society_rss_url",
        # International news
        "world": "world_rss_url",
        "international": "world_rss_url",
        "international news": "world_rss_url",
        "global": "world_rss_url",
        "global news": "world_rss_url",
        # Finance news
        "finance": "finance_rss_url",
        "finance news": "finance_rss_url",
        "financial": "finance_rss_url",
        "economy": "finance_rss_url",
        "economic": "finance_rss_url",
        "economic news": "finance_rss_url",
    }

    # Convert to lowercase and trim whitespace
    normalized_category = category_text.lower().strip()

    # Return the mapping result; if there is no match, return the original input
    return category_map.get(normalized_category, category_text)


@register_function(
    "get_news_from_chinanews",
    GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
async def get_news_from_chinanews(
    conn: "ConnectionHandler",
    category: str = None,
    detail: bool = False,
    lang: str = "zh_CN",
):
    """Fetch news and randomly select one to report, or retrieve the details of the previous news item"""
    try:
        # If detail is true, retrieve the details of the previous news item
        if detail:
            if (
                not hasattr(conn, "last_news_link")
                or not conn.last_news_link
                or "link" not in conn.last_news_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "Sorry, I could not find the most recent news query. Please fetch a news item first.",
                    None,
                )

            link = conn.last_news_link.get("link")
            title = conn.last_news_link.get("title", "Unknown title")

            if link == "#":
                return ActionResponse(
                    Action.REQLLM, "Sorry, that news item does not have a usable link for detailed content.", None
                )

            logger.bind(tag=TAG).debug(f"Fetching news details: {title}, URL={link}")

            # Fetch the news details
            detail_content = await fetch_news_detail(link)

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
                f"Detailed content: {detail_content}\n\n"
                f"(Please summarize the above news content, extract the key information, and present it naturally and fluently to the user,"
                f"without mentioning that it is a summary, as if you were narrating a complete news story)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Otherwise, fetch the news list and select one at random
        # Read the RSS URL from the configuration
        rss_config = conn.config.get("plugins", {}).get("get_news_from_chinanews", {})
        default_rss_url = rss_config.get(
            "default_rss_url", "https://www.chinanews.com.cn/rss/society.xml"
        )

        # Map the user's category input to the category key in the configuration
        mapped_category = map_category(category)

        # If a category is provided, try to fetch the corresponding URL from the configuration
        rss_url = default_rss_url
        if mapped_category and mapped_category in rss_config:
            rss_url = rss_config[mapped_category]

        logger.bind(tag=TAG).info(
            f"Fetching news: original category={category}, mapped category={mapped_category}, URL={rss_url}"
        )

        # Fetch the news list
        news_items = await fetch_news_from_rss(rss_url)

        if not news_items:
            return ActionResponse(
                Action.REQLLM, "Sorry, I could not retrieve any news information. Please try again later.", None
            )

        # Randomly select a news item
        selected_news = random.choice(news_items)

        # Save the current news link to the connection object so it can be queried later for details
        if not hasattr(conn, "last_news_link"):
            conn.last_news_link = {}
        conn.last_news_link = {
            "link": selected_news.get("link", "#"),
            "title": selected_news.get("title", "Unknown title"),
        }

        # Build the news report
        news_report = (
            f"Based on the following data, respond to the user's news query in {lang}:\n\n"
            f"News title: {selected_news['title']}\n"
            f"Publication time: {selected_news['pubDate']}\n"
            f"News content: {selected_news['description']}\n"
            f"(Please announce the news naturally and fluently, summarizing it as needed,"
            f"and read it directly without extra filler."
            f"If the user asks for more details, tell them they can say 'please explain this news in more detail' to get more content)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"An error occurred while fetching news: {e}")
        return ActionResponse(
            Action.REQLLM, "Sorry, an error occurred while fetching the news. Please try again later.", None
        )
