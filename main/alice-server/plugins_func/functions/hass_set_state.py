import httpx
from config.logger import setup_logging
from plugins_func.functions.hass_init import initialize_hass_handler
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

hass_set_state_function_desc = {
    "type": "function",
    "function": {
        "name": "hass_set_state",
        "description": "Set the state of a device in Home Assistant, including turning devices on or off, adjusting light brightness and color temperature, adjusting media player volume, and pausing, resuming, or muting devices.",
        "parameters": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "description": "The action to perform: turn on the device (turn_on), turn off the device (turn_off), increase brightness (brightness_up), decrease brightness (brightness_down), set brightness (brightness_value), increase volume (volume_up), decrease volume (volume_down), set volume (volume_set), set color temperature (set_kelvin), set color (set_color), pause the device (pause), resume the device (continue), or mute/unmute (volume_mute).",
                        },
                        "input": {
                            "type": "integer",
                            "description": "Only needed when setting volume or brightness. Valid values are 1-100, corresponding to 1%-100% volume or brightness.",
                        },
                        "is_muted": {
                            "type": "string",
                            "description": "Only needed for mute operations. Use true to mute and false to unmute.",
                        },
                        "rgb_color": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Only needed when setting a color; provide the target RGB values here.",
                        },
                    },
                    "required": ["type"],
                },
                "entity_id": {
                    "type": "string",
                    "description": "The device ID to operate on, the entity_id in Home Assistant.",
                },
            },
            "required": ["state", "entity_id"],
        },
    },
}


@register_function("hass_set_state", hass_set_state_function_desc, ToolType.SYSTEM_CTL)
async def hass_set_state(conn: "ConnectionHandler", entity_id="", state=None):
    if state is None:
        state = {}
    try:
        ha_response = await handle_hass_set_state(conn, entity_id, state)
        return ActionResponse(Action.REQLLM, ha_response, None)
    except httpx.TimeoutException:
        logger.bind(tag=TAG).error("Timed out while setting the Home Assistant state")
        return ActionResponse(Action.ERROR, "Request timed out", None)
    except Exception as e:
        error_msg = "Failed to execute the Home Assistant operation"
        logger.bind(tag=TAG).error(error_msg)
        return ActionResponse(Action.ERROR, error_msg, None)


async def handle_hass_set_state(conn: "ConnectionHandler", entity_id, state):
    ha_config = initialize_hass_handler(conn)
    api_key = ha_config.get("api_key")
    base_url = ha_config.get("base_url")
    """
    state = { "type":"brightness_up","input":"80","is_muted":"true"}
    """
    domains = entity_id.split(".")
    if len(domains) > 1:
        domain = domains[0]
    else:
        return "Operation failed: invalid device ID"
    action = ""
    arg = ""
    value = ""
    if state["type"] == "turn_on":
        description = "Device turned on"
        if domain == "cover":
            action = "open_cover"
        elif domain == "vacuum":
            action = "start"
        else:
            action = "turn_on"
    elif state["type"] == "turn_off":
        description = "Device turned off"
        if domain == "cover":
            action = "close_cover"
        elif domain == "vacuum":
            action = "stop"
        else:
            action = "turn_off"
    elif state["type"] == "brightness_up":
        description = "Light brightness increased"
        action = "turn_on"
        arg = "brightness_step_pct"
        value = 10
    elif state["type"] == "brightness_down":
        description = "Light brightness decreased"
        action = "turn_on"
        arg = "brightness_step_pct"
        value = -10
    elif state["type"] == "brightness_value":
        description = f"Brightness adjusted to {state['input']}"
        action = "turn_on"
        arg = "brightness_pct"
        value = state["input"]
    elif state["type"] == "set_color":
        description = f"Color adjusted to {state['rgb_color']}"
        action = "turn_on"
        arg = "rgb_color"
        value = state["rgb_color"]
    elif state["type"] == "set_kelvin":
        description = f"Color temperature adjusted to {state['input']}K"
        action = "turn_on"
        arg = "kelvin"
        value = state["input"]
    elif state["type"] == "volume_up":
        description = "Volume increased"
        action = state["type"]
    elif state["type"] == "volume_down":
        description = "Volume decreased"
        action = state["type"]
    elif state["type"] == "volume_set":
        description = f"Volume adjusted to {state['input']}"
        action = state["type"]
        arg = "volume_level"
        value = state["input"]
        if state["input"] >= 1:
            value = state["input"] / 100
    elif state["type"] == "volume_mute":
        description = "Device muted"
        action = state["type"]
        arg = "is_volume_muted"
        value = state["is_muted"]
    elif state["type"] == "pause":
        description = "Device paused"
        action = state["type"]
        if domain == "media_player":
            action = "media_pause"
        if domain == "cover":
            action = "stop_cover"
        if domain == "vacuum":
            action = "pause"
    elif state["type"] == "continue":
        description = "Device resumed"
        if domain == "media_player":
            action = "media_play"
        if domain == "vacuum":
            action = "start"
    else:
        return f"{domain} {state['type']} is not supported yet"

    if arg == "":
        data = {
            "entity_id": entity_id,
        }
    else:
        data = {"entity_id": entity_id, arg: value}
    url = f"{base_url}/api/services/{domain}/{action}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        response = await client.post(url, headers=headers, json=data)

    logger.bind(tag=TAG).info(
        f"Setting state: {description}, url: {url}, return code: {response.status_code}"
    )
    if response.status_code == 200:
        return description
    else:
        return f"Setting failed with error code: {response.status_code}"
