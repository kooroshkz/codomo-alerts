import random
from datetime import datetime, time

from codomo_alerts import schedule
from codomo_alerts.config import MIN_INTERVAL, Schedule

AMS = schedule.AMS


def at(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=AMS)


def test_windows():
    assert schedule.window(at(2026, 11, 3, 10)) == "release hours"   # Tuesday morning
    assert schedule.window(at(2026, 11, 3, 0, 15)) == "release hours"  # nightly batch
    assert schedule.window(at(2026, 11, 7, 10)) == "daytime"          # Saturday
    assert schedule.window(at(2026, 11, 3, 19)) == "daytime"
    assert schedule.window(at(2026, 11, 3, 3)) == "night"


def test_delay_follows_window_and_never_goes_below_minimum():
    s = Schedule(hot=120, day=300, night=900, jitter=0.25)
    rng = random.Random(1)
    for _ in range(50):
        assert 90 <= schedule.next_delay(s, at(2026, 11, 3, 10), rng) <= 150
        assert 675 <= schedule.next_delay(s, at(2026, 11, 3, 3), rng) <= 1125
    fast = Schedule(hot=30, jitter=0.5)
    assert all(schedule.next_delay(fast, at(2026, 11, 3, 10), rng) >= MIN_INTERVAL for _ in range(50))


def test_register_interest_homes_are_checked_less_often():
    assert schedule.interest_due_every(Schedule(interest=600)) == 600
    assert schedule.interest_due_every(Schedule(interest=10)) == MIN_INTERVAL


def test_quiet_hours_across_midnight():
    hours = (time(23, 0), time(7, 0))
    assert schedule.quiet(hours, at(2026, 11, 3, 23, 30))
    assert schedule.quiet(hours, at(2026, 11, 3, 6, 59))
    assert not schedule.quiet(hours, at(2026, 11, 3, 7, 0))
    assert not schedule.quiet(None, at(2026, 11, 3, 2))
