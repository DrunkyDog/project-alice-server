import requests
from requests.exceptions import RequestException
from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.agent_id = config.get("agent_id")  # Corresponds to agent_id
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", config.get("url"))  # Default to use base_url
        self.api_url = f"{self.base_url}/api/conversation/process"  # Splice complete API URL

    def response(self, session_id, dialogue, **kwargs):
        # Home assistant voice assistant has built-in intent, no need to use xiaozhi ai's built-in, just pass what user says to home assistant

        # Extract the content of the last 'user' role
        input_text = None
        if isinstance(dialogue, list):  # Ensure dialogue is a list
            # Reverse traverse to find the last 'user' role message
            for message in reversed(dialogue):
                if message.get("role") == "user":  # Find message with 'user' role
                    input_text = message.get("content", "")
                    break  # Exit loop immediately after finding

        # Construct request data
        payload = {
            "text": input_text,
            "agent_id": self.agent_id,
            "conversation_id": session_id,  # Use session_id as conversation_id
        }
        # Set request headers
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Initiate POST request
        with requests.post(self.api_url, json=payload, headers=headers) as response:
            # Check if request is successful
            response.raise_for_status()

            # Parse returned data
            data = response.json()
        speech = (
            data.get("response", {})
            .get("speech", {})
            .get("plain", {})
            .get("speech", "")
        )

        # Return generated content
        if speech:
            yield speech
        else:
            logger.bind(tag=TAG).warning("API returned data does not have speech content")

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).error(
            f"homeassistant does not support (function call), recommend using other intent recognition"
        )
