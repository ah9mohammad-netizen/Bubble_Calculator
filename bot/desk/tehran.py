"""Tehran clock + Jalali calendar, with no third-party dependencies.

The upstream desk used `pytz` + `jdatetime`. Both are replaced here so the
feature adds nothing to the Railway build that the signalling bot does not
already install. Iran abolished DST in 2022, so Asia/Tehran is a fixed
UTC+03:30 — which is exactly what the rest of this bot already assumes.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta

OFFSET = timedelta(hours=3, minutes=30)

_G_DAYS = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
JMONTHS = ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
           "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند")


def now() -> datetime:
    """Wall-clock time in Tehran, as a naive datetime (same convention as
    the rest of the bot, which adds the offset and formats)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + OFFSET


def to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    """Gregorian -> Jalali (Solar Hijri). Standard integer algorithm."""
    if gy > 1600:
        jy, gy = 979, gy - 1600
    else:
        jy, gy = 0, gy - 621
    gy2 = gy + 1 if gm > 2 else gy
    days = (365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
            - 80 + gd + _G_DAYS[gm - 1])
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        return jy, 1 + days // 31, 1 + days % 31
    return jy, 7 + (days - 186) // 30, 1 + (days - 186) % 30


def stamp() -> str:
    """`1405/06/11  14:05 Tehran` — the header on every desk message."""
    t = now()
    jy, jm, jd = to_jalali(t.year, t.month, t.day)
    return f"{jy:04d}/{jm:02d}/{jd:02d}  {t:%H:%M} Tehran"


def minutes_of_day() -> int:
    t = now()
    return t.hour * 60 + t.minute
