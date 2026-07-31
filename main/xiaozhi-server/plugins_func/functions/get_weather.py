# Weather plugin — 3-tier fallback chain:
#   1. OpenWeatherMap  (plugins.get_weather.owm_api_key) — 5-day forecast, native lang=th
#   2. WeatherAPI.com  (plugins.get_weather.api_key)     — 3-day forecast, UV, PM2.5
#   3. Open-Meteo      (no key required)                 — 7-day forecast
import json
import httpx
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Get current weather and multi-day forecast for a location. "
            "The user should provide a city or place name, e.g. 'Bangkok', 'กรุงเทพ', 'เชียงใหม่'. "
            "If no location is given, the city resolved from the client IP is used, "
            "otherwise the configured default city. "
            "Important: the local weather forecast is already provided in the context; "
            "do not call this tool when the user has not specified another city."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City or place name in any language, e.g. กรุงเทพ / Bangkok / เชียงใหม่. Optional; if not provided, it is omitted.",
                },
                "lang": {
                    "type": "string",
                    "description": "Language code of the user, e.g. th_TH / en_US / zh_CN. Defaults to th_TH.",
                },
            },
            "required": ["lang"],
        },
    },
}

HEADERS = {"User-Agent": "xiaozhi-esp32-server/1.0"}

TIMEOUT = httpx.Timeout(10.0, connect=3.0)

# WMO weather interpretation codes -> Thai description (Open-Meteo fallback only)
WMO_TH = {
    0: "ท้องฟ้าแจ่มใส", 1: "แจ่มใสเป็นส่วนใหญ่", 2: "มีเมฆบางส่วน", 3: "เมฆมาก",
    45: "หมอก", 48: "หมอกน้ำแข็ง",
    51: "ฝนปรอยเบา", 53: "ฝนปรอย", 55: "ฝนปรอยหนัก",
    56: "ฝนปรอยเย็นจัด", 57: "ฝนปรอยเย็นจัดหนัก",
    61: "ฝนเบา", 63: "ฝนปานกลาง", 65: "ฝนหนัก",
    66: "ฝนเย็นจัด", 67: "ฝนเย็นจัดหนัก",
    71: "หิมะเบา", 73: "หิมะปานกลาง", 75: "หิมะหนัก", 77: "เม็ดหิมะ",
    80: "ฝนซู่เบา", 81: "ฝนซู่ปานกลาง", 82: "ฝนซู่รุนแรง",
    85: "หิมะซู่เบา", 86: "หิมะซู่หนัก",
    95: "พายุฝนฟ้าคะนอง", 96: "พายุฝนฟ้าคะนองลูกเห็บเล็ก", 99: "พายุฝนฟ้าคะนองลูกเห็บใหญ่",
}


def _wmo_desc(code):
    try:
        return WMO_TH.get(int(code), f"สภาพอากาศรหัส {code}")
    except (TypeError, ValueError):
        return "ไม่ทราบ"


async def _get(client, url, params):
    return await client.get(url, params=params, headers=HEADERS)


# ---------- OpenWeatherMap (tier 1) ----------


async def _owm_report(api_key, location, lang_short):
    base = "https://api.openweathermap.org/data/2.5"
    params = {"q": location, "appid": api_key, "units": "metric", "lang": lang_short}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await _get(client, f"{base}/weather", params)
        if r.status_code == 404:
            return None  # location not found — let caller try next tier
        r.raise_for_status()
        cur = r.json()
        rf = await _get(client, f"{base}/forecast", params)
        rf.raise_for_status()
        fc = rf.json()

    place = cur.get("name") or location
    country = cur.get("sys", {}).get("country", "")
    if country:
        place += f" ({country})"

    w = (cur.get("weather") or [{}])[0]
    m = cur.get("main", {})
    wind_kph = round(cur.get("wind", {}).get("speed", 0) * 3.6, 1)

    report = (
        f"ตำแหน่งที่ค้นหา: {place}\n\n"
        f"สภาพอากาศปัจจุบัน: {w.get('description', 'ไม่ทราบ')}\n"
        f"  · อุณหภูมิ: {m.get('temp')}°C (รู้สึกเหมือน {m.get('feels_like')}°C)\n"
        f"  · ความชื้น: {m.get('humidity')}%\n"
        f"  · ลม: {wind_kph} กม./ชม.\n\n"
        "พยากรณ์ 5 วัน:\n"
    )

    # aggregate 3-hour buckets into daily min/max, max rain chance, midday condition
    daily = {}
    for item in fc.get("list", []):
        dt_txt = item.get("dt_txt", "")
        date = dt_txt.split(" ")[0]
        if not date:
            continue
        d = daily.setdefault(date, {"lo": None, "hi": None, "pop": 0.0, "desc": ""})
        tmin = item.get("main", {}).get("temp_min")
        tmax = item.get("main", {}).get("temp_max")
        if tmin is not None:
            d["lo"] = tmin if d["lo"] is None else min(d["lo"], tmin)
        if tmax is not None:
            d["hi"] = tmax if d["hi"] is None else max(d["hi"], tmax)
        d["pop"] = max(d["pop"], item.get("pop", 0) or 0)
        if " 12:00:00" in dt_txt or not d["desc"]:
            d["desc"] = (item.get("weather") or [{}])[0].get("description", "")
    for date in sorted(daily):
        d = daily[date]
        report += (
            f"{date}: {d['desc']}, {d['lo']}~{d['hi']}°C, "
            f"โอกาสฝน {round(d['pop'] * 100)}%\n"
        )

    report += "\n(ข้อมูลจาก OpenWeatherMap หากต้องการรายละเอียดวันใดบอกได้เลย)"
    return report


# ---------- WeatherAPI.com (tier 2) ----------


async def _weatherapi_report(api_key, location, lang_short):
    url = "https://api.weatherapi.com/v1/forecast.json"
    params = {
        "key": api_key,
        "q": location,
        "days": 3,  # free tier max
        "lang": lang_short,
        "aqi": "yes",
        "alerts": "no",
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await _get(client, url, params)
    if r.status_code == 400 and r.json().get("error", {}).get("code") == 1006:
        return None  # location not found — let caller try next tier
    r.raise_for_status()
    data = r.json()

    loc = data["location"]
    cur = data["current"]
    days = data["forecast"]["forecastday"]

    place = loc["name"]
    region = loc.get("region", "")
    if region and region != place:
        place += f" ({region}, {loc.get('country', '')})"
    elif loc.get("country"):
        place += f" ({loc['country']})"

    aqi = cur.get("air_quality", {})
    pm25 = aqi.get("pm2_5")
    pm25_line = f"  · PM2.5: {pm25:.1f} µg/m³\n" if isinstance(pm25, (int, float)) else ""

    report = (
        f"ตำแหน่งที่ค้นหา: {place}\n\n"
        f"สภาพอากาศปัจจุบัน: {cur['condition']['text']}\n"
        f"  · อุณหภูมิ: {cur['temp_c']}°C (รู้สึกเหมือน {cur['feelslike_c']}°C)\n"
        f"  · ความชื้น: {cur['humidity']}%\n"
        f"  · ลม: {cur['wind_kph']} กม./ชม.\n"
        f"  · UV index: {cur.get('uv', '?')}\n"
        f"{pm25_line}\n"
        "พยากรณ์ 3 วัน:\n"
    )
    for d in days:
        day = d["day"]
        report += (
            f"{d['date']}: {day['condition']['text']}, "
            f"{day['mintemp_c']}~{day['maxtemp_c']}°C, "
            f"โอกาสฝน {day.get('daily_chance_of_rain', '?')}%\n"
        )
    report += "\n(ข้อมูลจาก WeatherAPI.com หากต้องการรายละเอียดวันใดบอกได้เลย)"
    return report


# ---------- Open-Meteo (tier 3) ----------


async def _geocode(client, location, lang_short):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": location, "count": 1, "language": lang_short, "format": "json"}
    r = await _get(client, url, params)
    r.raise_for_status()
    results = r.json().get("results") or []
    if not results:
        return None
    g = results[0]
    return {
        "name": g.get("name", location),
        "admin": g.get("admin1", ""),
        "country": g.get("country", ""),
        "lat": g["latitude"],
        "lon": g["longitude"],
    }


async def _forecast(client, lat, lon):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                   "weather_code,wind_speed_10m,precipitation",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 7,
    }
    r = await _get(client, url, params)
    r.raise_for_status()
    return r.json()


async def _openmeteo_report(location, lang_short):
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        geo = await _geocode(client, location, lang_short)
        if not geo:
            geo = await _geocode(client, location, "en")
        if not geo:
            return None
        data = await _forecast(client, geo["lat"], geo["lon"])

    cur = data.get("current", {})
    daily = data.get("daily", {})

    place = geo["name"]
    if geo["admin"] and geo["admin"] != geo["name"]:
        place += f" ({geo['admin']}, {geo['country']})"
    elif geo["country"]:
        place += f" ({geo['country']})"

    report = (
        f"ตำแหน่งที่ค้นหา: {place}\n\n"
        f"สภาพอากาศปัจจุบัน: {_wmo_desc(cur.get('weather_code'))}\n"
        f"  · อุณหภูมิ: {cur.get('temperature_2m')}°C (รู้สึกเหมือน {cur.get('apparent_temperature')}°C)\n"
        f"  · ความชื้น: {cur.get('relative_humidity_2m')}%\n"
        f"  · ลม: {cur.get('wind_speed_10m')} กม./ชม.\n"
        f"  · ปริมาณฝน: {cur.get('precipitation')} มม.\n\n"
        "พยากรณ์ 7 วัน:\n"
    )
    dates = daily.get("time", [])
    codes = daily.get("weather_code", [])
    tmax = daily.get("temperature_2m_max", [])
    tmin = daily.get("temperature_2m_min", [])
    rain = daily.get("precipitation_probability_max", [])
    for i, d in enumerate(dates):
        code = codes[i] if i < len(codes) else None
        hi = tmax[i] if i < len(tmax) else "?"
        lo = tmin[i] if i < len(tmin) else "?"
        rp = rain[i] if i < len(rain) else "?"
        report += f"{d}: {_wmo_desc(code)}, {lo}~{hi}°C, โอกาสฝน {rp}%\n"

    report += "\n(ข้อมูลจาก Open-Meteo หากต้องการรายละเอียดวันใดบอกได้เลย)"
    return report


def _resolve_location(conn: "ConnectionHandler", default_location: str) -> str:
    """Resolve the city from the client IP, falling back to the configured default."""
    from core.utils.cache.manager import cache_manager, CacheType

    client_ip = conn.client_ip
    if not client_ip:
        return default_location

    # Try the cache first for the IP-to-city mapping.
    cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
    if cached_ip_info:
        return cached_ip_info.get("city") or default_location

    # Cache miss; call the API to retrieve it.
    ip_info = get_ip_info(client_ip, logger)
    if ip_info:
        cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
        return ip_info.get("city") or default_location

    return default_location


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def get_weather(
    conn: "ConnectionHandler", location: str = None, lang: str = "th_TH"
):
    from core.utils.cache.manager import cache_manager, CacheType

    weather_config = conn.config.get("plugins", {}).get("get_weather", {})
    # manager-api may deliver plugin params as a JSON string instead of a dict
    if isinstance(weather_config, str):
        try:
            weather_config = json.loads(weather_config)
        except ValueError:
            weather_config = {}
    default_location = weather_config.get("default_location", "Bangkok")
    api_key = (weather_config.get("api_key") or "").strip()
    owm_key = (weather_config.get("owm_api_key") or "").strip()

    # Prioritize the location provided by the user.
    if not location:
        location = _resolve_location(conn, default_location)

    lang_short = (lang or "th").split("_")[0].split("-")[0] or "th"

    # Try to retrieve the full weather report from the cache.
    cache_key = f"full_weather_{location}_{lang_short}"
    cached_weather_report = cache_manager.get(CacheType.WEATHER, cache_key)
    if cached_weather_report:
        return ActionResponse(Action.REQLLM, cached_weather_report, None)

    report = None
    if owm_key:
        try:
            report = await _owm_report(owm_key, location, lang_short)
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.bind(tag=TAG).warning(
                f"OpenWeatherMap failed ({e}), falling back to WeatherAPI"
            )
    else:
        logger.bind(tag=TAG).warning("No OpenWeatherMap key configured")

    if report is None and api_key:
        try:
            report = await _weatherapi_report(api_key, location, lang_short)
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.bind(tag=TAG).warning(
                f"WeatherAPI failed ({e}), falling back to Open-Meteo"
            )

    if report is None:
        try:
            report = await _openmeteo_report(location, lang_short)
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.bind(tag=TAG).error(f"Open-Meteo request failed: {e}")
            return ActionResponse(Action.REQLLM, None, "เรียกบริการสภาพอากาศไม่สำเร็จ")

    if report is None:
        return ActionResponse(
            Action.REQLLM,
            f"ไม่พบเมืองชื่อ '{location}' กรุณาตรวจสอบชื่อเมืองอีกครั้ง",
            None,
        )

    # Cache the full weather report.
    cache_manager.set(CacheType.WEATHER, cache_key, report)
    return ActionResponse(Action.REQLLM, report, None)
