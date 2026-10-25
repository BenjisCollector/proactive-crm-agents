"""Deterministic parts: the stale-deal rule score and the calendar free-slot finder. The LLM only adjusts / chooses."""
from datetime import datetime, timedelta

from .db import FX_TO_USD, STALE_DAYS, today

SUN_THU = {"KSA", "Kuwait", "Qatar"}  # customer weekend is Fri/Sat; the rep (UAE) works Mon-Fri
AR_DAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
AR_MONTHS = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def to_usd(amount: float, currency: str) -> float:
    return amount * FX_TO_USD[currency]


def rule_score(stage: str, idle: int, amount_usd: float, close_in_days: int) -> tuple[bool, int]:
    """(flagged, 0-100). Flagged once idle days reach the stage threshold; score grows with idleness, value, closing date."""
    ratio = idle / STALE_DAYS[stage]
    if ratio < 1:
        return False, int(ratio * 40)
    score = 50 + min(25, (ratio - 1) * 25)
    score += 10 if amount_usd >= 250_000 else 5 if amount_usd >= 100_000 else 0
    score += 10 if close_in_days <= 21 else 0
    return True, min(100, round(score))


def level(risk: int) -> str:
    return "high" if risk >= 75 else "medium" if risk >= 60 else "low"


def free_slots(conn, country: str, days: int = 8, limit: int = 6) -> list[datetime]:
    """Candidate 30-min slots (Dubai time) that avoid the rep's busy blocks and both sides' weekends / Friday prayer."""
    busy = [(datetime.fromisoformat(s), datetime.fromisoformat(e)) for s, e in conn.execute("SELECT start,end FROM calendar")]
    out: list[datetime] = []
    for n in range(1, days + 1):
        day = today() + timedelta(days=n)
        wd = day.weekday()  # Mon=0
        if wd > 4 or (wd == 4 and country in SUN_THU):
            continue
        for hour in (10, 11) if wd == 4 else (10, 11, 14, 15):
            s = datetime(day.year, day.month, day.day, hour)
            if not any(s < be and s + timedelta(minutes=30) > bs for bs, be in busy):
                out.append(s)
    return out[:limit]


def fmt_slot(dt: datetime, lang: str) -> str:
    if lang == "ar":
        h12 = dt.hour % 12 or 12
        return f"{AR_DAYS[dt.weekday()]} {dt.day} {AR_MONTHS[dt.month - 1]}، الساعة {h12}:{dt.minute:02d} {'صباحاً' if dt.hour < 12 else 'مساءً'} بتوقيت دبي"
    return dt.strftime(f"%A {dt.day} %B, %H:%M") + " Dubai time"
