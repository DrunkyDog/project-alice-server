import os
import re
import json

import requests

from plugins_func.register import register_function, ToolType, ActionResponse, Action

GET_DIRECTIONS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_directions",
        "description": (
            "Get travel directions, distance and estimated time between two places using "
            "Google Maps. Use whenever the user asks how to get somewhere, the route, "
            "travel time, or distance — e.g. 'ไปสยามยังไง', 'จากบ้านไปสนามบินไกลไหม', "
            "'ขับรถจาก A ไป B ใช้เวลาเท่าไหร่', 'นั่งรถไฟฟ้าจาก A ไป B'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Start place or address, e.g. 'สยามพารากอน', 'บ้าน', a landmark name",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination place or address, e.g. 'สนามบินสุวรรณภูมิ'",
                },
                "mode": {
                    "type": "string",
                    "description": "Travel mode. Default driving.",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                },
            },
            "required": ["origin", "destination"],
        },
    },
}

_STRIP_HTML = re.compile(r"<[^>]+>")
_MODE_TH = {
    "driving": "ขับรถ",
    "walking": "เดิน",
    "transit": "ขนส่งสาธารณะ",
    "bicycling": "จักรยาน",
}


def _get_api_key(conn):
    cfg = conn.config.get("plugins", {}).get("get_directions", {}) if conn else {}
    if isinstance(cfg, str):
        try:
            cfg = json.loads(cfg)
        except Exception:
            cfg = {}
    return (cfg.get("api_key") or os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()


@register_function("get_directions", GET_DIRECTIONS_FUNCTION_DESC, ToolType.SYSTEM_CTL)
def get_directions(conn, origin: str, destination: str, mode: str = "driving"):
    api_key = _get_api_key(conn)
    if not api_key:
        return ActionResponse(Action.REQLLM, None, "ยังไม่ได้ตั้งค่า Google Maps API key")

    mode = (mode or "driving").lower()
    if mode not in _MODE_TH:
        mode = "driving"

    params = {
        "origin": origin,
        "destination": destination,
        "mode": mode,
        "language": "th",
        "region": "th",
        "key": api_key,
    }
    if mode == "transit":
        params["departure_time"] = "now"

    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params=params,
            timeout=15,
        )
        data = r.json()
    except Exception as e:
        return ActionResponse(
            Action.REQLLM, None, f"เรียกบริการแผนที่ไม่สำเร็จ: {e}"
        )

    status = data.get("status")
    if status != "OK" or not data.get("routes"):
        msg = data.get("error_message") or status or "ไม่พบเส้นทาง"
        return ActionResponse(Action.REQLLM, None, f"หาเส้นทางไม่สำเร็จ ({msg})")

    leg = data["routes"][0]["legs"][0]
    distance = leg.get("distance", {}).get("text", "-")
    duration = leg.get("duration", {}).get("text", "-")
    dur_traffic = (leg.get("duration_in_traffic") or {}).get("text")
    start_addr = leg.get("start_address", origin)
    end_addr = leg.get("end_address", destination)
    mode_th = _MODE_TH.get(mode, mode)

    steps = []
    for s in leg.get("steps", [])[:6]:
        instr = _STRIP_HTML.sub("", s.get("html_instructions", "")).strip()
        d = s.get("distance", {}).get("text", "")
        if instr:
            steps.append(f"- {instr} ({d})" if d else f"- {instr}")

    summary = (
        f"เส้นทาง{mode_th} จาก {start_addr} ไป {end_addr}\n"
        f"ระยะทาง {distance} ใช้เวลาประมาณ {dur_traffic or duration}"
    )
    if steps:
        summary += "\nเส้นทางโดยสรุป:\n" + "\n".join(steps)

    return ActionResponse(Action.REQLLM, summary, None)
