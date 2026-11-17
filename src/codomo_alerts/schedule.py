"""When to check. All times are Amsterdam time, whatever the server's clock zone is."""

from __future__ import annotations

import random
from datetime import datetime, time
from zoneinfo import ZoneInfo

from .config import MIN_INTERVAL, Schedule

AMS = ZoneInfo("Europe/Amsterdam")

# Most homes are released on weekdays during office hours, plus a small batch just after
# midnight when unpaid reservations go back on sale (seen again on Codomo, 2026-11-16 00:16).
RELEASE_WINDOWS = [
    (range(0, 5), time(8, 30), time(18, 0)),
    (range(0, 7), time(0, 5), time(0, 45)),
]
DAY = (time(7, 0), time(23, 30))


def local(now: datetime | None = None) -> datetime:
    return (now or datetime.now(AMS)).astimezone(AMS)


def _within(t: time, start: time, end: time) -> bool:
    return start <= t < end if start <= end else (t >= start or t < end)


def window(now: datetime | None = None) -> str:
    n = local(now)
    for days, start, end in RELEASE_WINDOWS:
        if n.weekday() in days and _within(n.time(), start, end):
            return "release hours"
    if _within(n.time(), *DAY):
        return "daytime"
    return "night"


def _jitter(seconds: float, amount: float, rng: random.Random | None) -> float:
    r = (rng or random).uniform(1 - amount, 1 + amount)
    return max(MIN_INTERVAL, seconds * r)


def next_delay(s: Schedule, now: datetime | None = None, rng: random.Random | None = None) -> float:
    base = {"release hours": s.hot, "daytime": s.day, "night": s.night}[window(now)]
    return _jitter(base, s.jitter, rng)


def interest_due_every(s: Schedule) -> float:
    """Register-interest homes have no deadline to race, so they are read less often."""
    return max(MIN_INTERVAL, s.interest)


def quiet(hours: tuple[time, time] | None, now: datetime | None = None) -> bool:
    return bool(hours) and _within(local(now).time(), *hours)
