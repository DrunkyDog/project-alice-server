from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "Used to retrieve lunar calendar and fortune information for a specific date."
            "The user can specify the content to query, such as lunar date, the sexagenary cycle, solar terms, zodiac sign, constellation, eight characters, or auspicious and inauspicious matters."
            "If no query content is specified, it defaults to the sexagenary year and lunar date."
            "For basic queries such as 'What is the lunar date today?' or 'What is the lunar date today?', use the context directly instead of calling this tool."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date to query, in YYYY-MM-DD format, for example 2024-01-01. If not provided, the current date is used.",
                },
                "query": {
                    "type": "string",
                    "description": "The content to query, for example lunar date, sexagenary cycle, holidays, solar terms, zodiac sign, constellation, eight characters, or auspicious and inauspicious matters.",
                },
            },
            "required": [],
        },
    },
}


@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(date=None, query=None):
    """
    Used to retrieve the current lunar calendar information, including the sexagenary cycle, solar terms, zodiac sign, constellation, eight characters, and fortune information.
    """
    from core.utils.cache.manager import cache_manager, CacheType

    # If a date is provided, use that date; otherwise use the current date.
    if date:
        try:
            now = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                f"Invalid date format. Please use YYYY-MM-DD, for example 2024-01-01",
                None,
            )
    else:
        now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")

    # If query is None, use the default text.
    if query is None:
        query = "Default query for the sexagenary year and lunar date"

    # Try to retrieve the lunar information from the cache.
    lunar_cache_key = f"lunar_info_{current_date}"
    cached_lunar_info = cache_manager.get(CacheType.LUNAR, lunar_cache_key)
    if cached_lunar_info:
        return ActionResponse(Action.REQLLM, cached_lunar_info, None)

    response_text = f"Respond to the user's query based on the following information and provide content related to {query}:\n"

    lunar = cnlunar.Lunar(now, godType="8char")
    response_text += (
        "Lunar information:\n"
        "%s year %s%s\n" % (lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn)
        + "Stem-branch: %s year %s month %s day\n" % (lunar.year8Char, lunar.month8Char, lunar.day8Char)
        + "Zodiac: %s\n" % (lunar.chineseYearZodiac)
        + "Eight characters: %s\n"
        % (
            " ".join(
                [lunar.year8Char, lunar.month8Char, lunar.day8Char, lunar.twohour8Char]
            )
        )
        + "Today's holiday: %s\n"
        % (
            ",".join(
                filter(
                    None,
                    (
                        lunar.get_legalHolidays(),
                        lunar.get_otherHolidays(),
                        lunar.get_otherLunarHolidays(),
                    ),
                )
            )
        )
        + "Today's solar term: %s\n" % (lunar.todaySolarTerms)
        + "Next solar term: %s %s year %s month %s day\n"
        % (
            lunar.nextSolarTerm,
            lunar.nextSolarTermYear,
            lunar.nextSolarTermDate[0],
            lunar.nextSolarTermDate[1],
        )
        + "This year's solar term table: %s\n"
        % (
            ", ".join(
                [
                    f"{term}({date[0]} month {date[1]} day)"
                    for term, date in lunar.thisYearSolarTermsDic.items()
                ]
            )
        )
        + "Zodiac clash: %s\n" % (lunar.chineseZodiacClash)
        + "Constellation: %s\n" % (lunar.starZodiac)
        + "Nayin: %s\n" % lunar.get_nayin()
        + "Peng Zu's taboos: %s\n" % (lunar.get_pengTaboo(delimit=", "))
        + "Day officer: %s position\n" % lunar.get_today12DayOfficer()[0]
        + "Day spirit: %s(%s)\n"
        % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2])
        + "Twenty-eight constellations: %s\n" % lunar.get_the28Stars()
        + "Lucky gods' direction: %s\n" % " ".join(lunar.get_luckyGodsDirection())
        + "Today's fetal god: %s\n" % lunar.get_fetalGod()
        + "Auspicious: %s\n" % "、".join(lunar.goodThing[:10])
        + "Inauspicious: %s\n" % "、".join(lunar.badThing[:10])
        + "(Return the sexagenary year and lunar date by default; only return today's auspicious and inauspicious information when the user asks for that information)"
    )

    # Cache the lunar information
    cache_manager.set(CacheType.LUNAR, lunar_cache_key, response_text)

    return ActionResponse(Action.REQLLM, response_text, None)
