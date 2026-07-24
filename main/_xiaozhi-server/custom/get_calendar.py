import os
import json
from datetime import datetime, timedelta

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from plugins_func.register import register_function, ToolType, ActionResponse, Action

CAL_SCOPE = "https://www.googleapis.com/auth/calendar"
API = "https://www.googleapis.com/calendar/v3/calendars"
TZ = os.getenv("GOOGLE_CALENDAR_TZ", "Asia/Bangkok")


def _sa_path():
    return os.getenv("GOOGLE_SA_JSON", "/opt/xiaozhi-esp32-server/data/google-tts-sa.json")


def _cal_id():
    return os.getenv("GOOGLE_CALENDAR_ID", "primary")


_session = None


def _svc():
    global _session
    if _session is None:
        creds = service_account.Credentials.from_service_account_file(
            _sa_path(), scopes=[CAL_SCOPE]
        )
        _session = AuthorizedSession(creds)
    return _session


def _dt_field(value):
    """Accept 'YYYY-MM-DD' (all-day) or RFC3339 datetime; return a Calendar start/end object."""
    if not value:
        return None
    if len(value) == 10 and value.count("-") == 2:  # date only
        return {"date": value}
    return {"dateTime": value, "timeZone": TZ}


def _fmt_event(ev):
    s = ev.get("start", {})
    when = s.get("dateTime") or s.get("date") or "?"
    loc = ev.get("location")
    line = f"- {ev.get('summary', '(ไม่มีชื่อ)')} | {when}"
    if loc:
        line += f" | ที่ {loc}"
    line += f" | id={ev.get('id')}"
    return line


# ------------------------------------------------------------------ create
CREATE_DESC = {
    "type": "function",
    "function": {
        "name": "calendar_create_event",
        "description": (
            "Create a new event in the user's Google Calendar. Use when the user wants to "
            "add/schedule an appointment or reminder, e.g. 'นัดหมอพรุ่งนี้ 10 โมง', "
            "'เพิ่มประชุมวันศุกร์บ่าย 2'. Compute the concrete date/time yourself and pass "
            "RFC3339 (e.g. 2026-07-23T10:00:00) in the user's local time; for a full-day "
            "event pass a date (2026-07-23)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title, e.g. 'นัดหมอฟัน'"},
                "start_datetime": {"type": "string", "description": "Start, RFC3339 or YYYY-MM-DD"},
                "end_datetime": {"type": "string", "description": "End, RFC3339 or YYYY-MM-DD. If omitted, +1 hour."},
                "description": {"type": "string", "description": "Optional details"},
                "location": {"type": "string", "description": "Optional place"},
            },
            "required": ["summary", "start_datetime"],
        },
    },
}


@register_function("calendar_create_event", CREATE_DESC, ToolType.SYSTEM_CTL)
def calendar_create_event(conn, summary, start_datetime, end_datetime=None,
                          description=None, location=None):
    start = _dt_field(start_datetime)
    if end_datetime:
        end = _dt_field(end_datetime)
    elif "date" in start:
        end = start  # all-day
    else:
        try:
            end_dt = datetime.fromisoformat(start_datetime) + timedelta(hours=1)
            end = {"dateTime": end_dt.isoformat(), "timeZone": TZ}
        except Exception:
            end = start
    body = {"summary": summary, "start": start, "end": end}
    if description:
        body["description"] = description
    if location:
        body["location"] = location
    try:
        r = _svc().post(f"{API}/{_cal_id()}/events", json=body, timeout=15)
    except Exception as e:
        return ActionResponse(Action.REQLLM, None, f"สร้างนัดหมายไม่สำเร็จ: {e}")
    if r.status_code not in (200, 201):
        return ActionResponse(Action.REQLLM, None, f"สร้างนัดหมายไม่สำเร็จ ({r.status_code}): {r.text[:200]}")
    ev = r.json()
    return ActionResponse(
        Action.REQLLM,
        f"สร้างนัดหมายแล้ว: {ev.get('summary')} เวลา "
        f"{ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')}",
        None,
    )


# ------------------------------------------------------------------ search
SEARCH_DESC = {
    "type": "function",
    "function": {
        "name": "calendar_search_events",
        "description": (
            "Search/list events in the user's Google Calendar. Use for 'สัปดาห์นี้มีนัดอะไรบ้าง', "
            "'พรุ่งนี้มีอะไร', 'หานัดหมอ'. Pass time_min/time_max as RFC3339 to bound the range "
            "(compute concrete dates yourself). Always call this first before deleting/updating to get the event id."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Optional keyword to match, e.g. 'หมอ'"},
                "time_min": {"type": "string", "description": "Range start RFC3339 (default now)"},
                "time_max": {"type": "string", "description": "Range end RFC3339"},
                "max_results": {"type": "integer", "description": "Max events, default 10"},
            },
            "required": [],
        },
    },
}


@register_function("calendar_search_events", SEARCH_DESC, ToolType.SYSTEM_CTL)
def calendar_search_events(conn, query=None, time_min=None, time_max=None, max_results=10):
    params = {
        "singleEvents": "true",
        "orderBy": "startTime",
        "maxResults": int(max_results or 10),
        "timeMin": time_min or datetime.now().astimezone().isoformat(),
    }
    if time_max:
        params["timeMax"] = time_max
    if query:
        params["q"] = query
    try:
        r = _svc().get(f"{API}/{_cal_id()}/events", params=params, timeout=15)
    except Exception as e:
        return ActionResponse(Action.REQLLM, None, f"ค้นหานัดหมายไม่สำเร็จ: {e}")
    if r.status_code != 200:
        return ActionResponse(Action.REQLLM, None, f"ค้นหานัดหมายไม่สำเร็จ ({r.status_code})")
    items = r.json().get("items", [])
    if not items:
        return ActionResponse(Action.REQLLM, "ไม่พบนัดหมายในช่วงเวลาที่ระบุ", None)
    lines = "\n".join(_fmt_event(e) for e in items)
    return ActionResponse(Action.REQLLM, f"พบ {len(items)} นัดหมาย:\n{lines}", None)


# ------------------------------------------------------------------ delete
DELETE_DESC = {
    "type": "function",
    "function": {
        "name": "calendar_delete_event",
        "description": (
            "Delete an event from the user's Google Calendar by event_id. **You MUST first "
            "call calendar_search_events to find the id, and confirm with the user before "
            "deleting** (deletion is irreversible)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event id from calendar_search_events"},
            },
            "required": ["event_id"],
        },
    },
}


@register_function("calendar_delete_event", DELETE_DESC, ToolType.SYSTEM_CTL)
def calendar_delete_event(conn, event_id):
    try:
        r = _svc().delete(f"{API}/{_cal_id()}/events/{event_id}", timeout=15)
    except Exception as e:
        return ActionResponse(Action.REQLLM, None, f"ลบนัดหมายไม่สำเร็จ: {e}")
    if r.status_code not in (200, 204):
        return ActionResponse(Action.REQLLM, None, f"ลบนัดหมายไม่สำเร็จ ({r.status_code})")
    return ActionResponse(Action.REQLLM, "ลบนัดหมายเรียบร้อยแล้ว", None)


# ------------------------------------------------------------------ update
UPDATE_DESC = {
    "type": "function",
    "function": {
        "name": "calendar_update_event",
        "description": (
            "Update an existing event (time, title, place). First call calendar_search_events "
            "to get the event_id. Only pass the fields that change."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "The event id from calendar_search_events"},
                "summary": {"type": "string", "description": "New title"},
                "start_datetime": {"type": "string", "description": "New start RFC3339 / YYYY-MM-DD"},
                "end_datetime": {"type": "string", "description": "New end RFC3339 / YYYY-MM-DD"},
                "location": {"type": "string", "description": "New place"},
                "description": {"type": "string", "description": "New details"},
            },
            "required": ["event_id"],
        },
    },
}


@register_function("calendar_update_event", UPDATE_DESC, ToolType.SYSTEM_CTL)
def calendar_update_event(conn, event_id, summary=None, start_datetime=None,
                          end_datetime=None, location=None, description=None):
    body = {}
    if summary:
        body["summary"] = summary
    if start_datetime:
        body["start"] = _dt_field(start_datetime)
    if end_datetime:
        body["end"] = _dt_field(end_datetime)
    if location:
        body["location"] = location
    if description:
        body["description"] = description
    if not body:
        return ActionResponse(Action.REQLLM, None, "ไม่มีข้อมูลที่จะแก้ไข")
    try:
        r = _svc().patch(f"{API}/{_cal_id()}/events/{event_id}", json=body, timeout=15)
    except Exception as e:
        return ActionResponse(Action.REQLLM, None, f"แก้ไขนัดหมายไม่สำเร็จ: {e}")
    if r.status_code != 200:
        return ActionResponse(Action.REQLLM, None, f"แก้ไขนัดหมายไม่สำเร็จ ({r.status_code})")
    ev = r.json()
    return ActionResponse(Action.REQLLM, f"แก้ไขนัดหมายแล้ว: {ev.get('summary')}", None)
