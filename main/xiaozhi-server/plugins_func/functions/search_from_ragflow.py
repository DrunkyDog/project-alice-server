import json
import httpx
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# Define the base function description template.
SEARCH_FROM_RAGFLOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_ragflow",
        "description": "Search for information in the knowledge base.",
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "The question to search for"}},
            "required": ["question"],
        },
    },
}


@register_function(
    "search_from_ragflow", SEARCH_FROM_RAGFLOW_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
async def search_from_ragflow(conn: "ConnectionHandler", question=None):
    # Ensure the string parameter is handled correctly.
    if question and isinstance(question, str):
        # Ensure the question parameter is a UTF-8 string.
        pass
    else:
        question = str(question) if question is not None else ""

    ragflow_config = conn.config.get("plugins", {}).get("search_from_ragflow", {})
    base_url = ragflow_config.get("base_url", "")
    api_key = ragflow_config.get("api_key", "")
    dataset_ids = ragflow_config.get("dataset_ids", [])

    url = base_url + "/api/v1/retrieval"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Ensure the strings in the payload are UTF-8 encoded.
    payload = {"question": question, "dataset_ids": dataset_ids}

    try:
        # Use ensure_ascii=False to ensure JSON serialization handles non-ASCII characters correctly.
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0), verify=False) as client:
            response = await client.post(url, json=payload, headers=headers)

        # Explicitly set the response encoding to UTF-8.
        response.encoding = "utf-8"

        response.raise_for_status()

        # First retrieve the text content, then manually decode the JSON.
        response_text = response.text

        result = json.loads(response_text)

        if result.get("code") != 0:
            error_detail = result.get("error", {}).get("detail", "Unknown error")
            error_message = result.get("error", {}).get("message", "")
            error_code = result.get("code", "")

            # Safely log the error information.
            logger.bind(tag=TAG).error(
                f"RAGFlow API call failed. Response code: {error_code}. Error detail: {error_detail}. Full response: {result}"
            )

            # Build a detailed error response.
            error_response = f"The RAG interface returned an exception (error code: {error_code})"

            if error_message:
                error_response += f": {error_message}"
            if error_detail:
                error_response += f"\nDetails: {error_detail}"

            return ActionResponse(Action.RESPONSE, None, error_response)

        chunks = result.get("data", {}).get("chunks", [])
        contents = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content:
                # Safely process the content string.
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, bytes):
                    contents.append(content.decode("utf-8", errors="replace"))
                else:
                    contents.append(str(content))

        if contents:
            # Organize the knowledge base content in a quoted format.
            context_text = f"# Information found in the knowledge base for the question '{question}'\n"
            context_text += "```\n\n\n".join(contents[:5])
            context_text += "\n```"
        else:
            context_text = "No relevant information was found in the knowledge base."
        return ActionResponse(Action.REQLLM, context_text, None)

    except httpx.TimeoutException as e:
        error_response = "RAG interface request timed out"
        error_response += "\nPossible cause: the RAGflow service is responding slowly or there is network latency"
        error_response += "\nSuggested action: please try again later or check the RAGflow service performance"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except httpx.HTTPStatusError as e:
        if hasattr(e.response, "status_code"):
            status_code = e.response.status_code
            error_response = f"RAG interface HTTP error (status code: {status_code})"
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
                if error_detail:
                    error_response += f"\nError detail: {error_detail}"
            except:
                pass
        else:
            error_response = f"RAG interface HTTP exception: {str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except httpx.HTTPError as e:
        error_response = "Unable to connect to the RAG interface"
        error_response += "\nPossible cause: the RAGflow service address is incorrect or the service is not running"
        error_response += "\nSuggested action: please check the RAGflow service address configuration and service status"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except Exception as e:
        # Other exceptions.
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGflow processing exception. Exception type: {error_type}. Details: {str(e)}"
        )

        # Provide detailed error information.
        error_response = f"RAG interface processing exception ({error_type}): {str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)
