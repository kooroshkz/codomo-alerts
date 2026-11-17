import random

import pytest
from conftest import Clock, FakeCodomo, FakeNotifier, home

from codomo_alerts.client import Blocked, Changed, Maintenance, RateLimited, Unavailable
from codomo_alerts.watcher import Watcher


@pytest.fixture
def setup(store, make_cfg):
    def make(homes=(), search=None, notify=None, notifier=None):
        site = FakeCodomo(list(homes))
        clock = Clock()
        n = notifier or FakeNotifier()
        cfg = make_cfg(search=search, notify=notify)
        w = Watcher(cfg, store, client=site, notifier=n, clock=clock, rng=random.Random(0))
        return w, site, n, clock
    return make


def test_first_check_says_hello_and_nothing_else(setup):
    w, site, n, clock = setup([home(1), home(2)])
    delay = w.tick()
    assert n.titles() == ["Watching Codomo"]
    assert "2 homes match right now" in n.sent[0][1]
    assert 60 <= delay <= 200
    assert w.store.get("status")["state"] == "watching"


def test_new_home_is_announced_with_details(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.add(home(2, name="Kastanjelaan 1-135", rent=1898, extra=100))
    clock.advance(minutes=2)
    w.tick()
    title, body = n.sent[-1]
    assert title == "Kastanjelaan 1-135"
    assert body == ("Eindhoven · Studio · €1,998\nIndefinite · Furnished\n"
                    "https://codomo.eu/homes/nl/en/eindhoven/test-tower/teststraat-2")
    w.tick()
    assert len(n.sent) == 2  # never twice


def test_taken_homes_are_quiet(setup):
    w, site, n, clock = setup([home(1), home(2)])
    w.tick()
    site.remove(2)
    for _ in range(3):
        clock.advance(minutes=2)
        w.tick()
    assert n.titles() == ["Watching Codomo"]
    assert w.store.q("SELECT COUNT(*) FROM events WHERE kind='gone'")[0][0] == 1


def test_many_new_homes_come_as_one_message(setup):
    w, site, n, clock = setup()
    w.tick()
    site.add(*[home(i) for i in range(10, 16)])
    clock.advance(minutes=2)
    w.tick()
    assert n.titles()[-1] == "6 new homes"


def test_register_interest_homes(setup):
    w, site, n, clock = setup()
    w.tick()
    site.add(home(30, direct=False, interest=41))
    clock.advance(minutes=15)
    w.tick()
    assert n.titles()[-1] == "Register interest (shortlist): Teststraat 30"
    assert "41 people showed interest" in n.sent[-1][1] and "shortlist" in n.sent[-1][1]


def test_interest_off(setup):
    w, site, n, clock = setup(search={"cities": ["Eindhoven"], "interest": False})
    w.tick()
    assert all(c[1]["publish_mode"] == "direct_booking" for c in site.calls)


def test_short_stays_are_never_announced_with_a_long_stay_search(setup):
    w, site, n, clock = setup([home(1)], search={"cities": ["Eindhoven"], "contract": ["long"]})
    w.tick()
    site.add(home(2, contract="6m"), home(3, contract="indefinite"))
    clock.advance(minutes=2)
    w.tick()
    assert n.titles()[-1] == "Teststraat 3" and "Teststraat 2" not in n.titles()
    pages = len(site.units)
    clock.advance(minutes=2)
    w.tick()
    assert len(site.units) == pages            # each home page is read once


def test_a_home_page_that_fails_waits_for_the_next_check(setup):
    w, site, n, clock = setup([home(1)], search={"cities": ["Eindhoven"], "contract": ["long"]})
    w.tick()
    site.add(home(2))
    site.unit_fail = Unavailable("down")
    clock.advance(minutes=2)
    w.tick()
    assert "Teststraat 2" not in n.titles()
    site.unit_fail = None
    clock.advance(minutes=2)
    w.tick()
    assert n.titles()[-1] == "Teststraat 2"


def test_blocked_pauses_tells_once_and_recovers(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = Blocked("Cloudflare is blocking automated requests")
    clock.advance(minutes=2)
    delay = w.tick()
    assert delay == 1800
    assert n.titles()[-1] == "Alerts paused"
    assert w.store.get("status")["state"] == "paused"

    before = site.requests
    clock.advance(minutes=10)
    w.tick()
    assert site.requests == before  # waits, does not ask again

    clock.advance(minutes=25)
    assert w.tick() == 3600  # still blocked: waits longer
    assert n.titles().count("Alerts paused") == 1

    site.fail = None
    clock.advance(hours=2)
    w.tick()
    assert n.titles()[-1] == "Alerts back on"
    assert w.store.get("failures") is None


def test_rate_limit_respects_retry_after(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = RateLimited("slow down", retry_after=240)
    clock.advance(minutes=2)
    assert w.tick() == 240
    assert n.titles() == ["Watching Codomo"]  # short pause, no notice


def test_short_outages_stay_quiet(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = Unavailable("down")
    clock.advance(minutes=2)
    assert w.tick() == 60
    clock.advance(minutes=2)
    assert w.tick() == 120
    assert n.titles() == ["Watching Codomo"]


def test_maintenance_is_a_short_quiet_pause(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = Maintenance("Codomo is down for maintenance")
    clock.advance(minutes=2)
    assert w.tick() == 60
    assert n.titles() == ["Watching Codomo"] and w.store.get("status")["state"] == "retrying"


def test_site_change_is_reported(setup):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = Changed("Codomo moved or removed the homes page")
    clock.advance(minutes=2)
    w.tick()
    assert n.titles()[-1] == "Alerts may be broken"


def test_failed_messages_are_retried(setup):
    flaky = FakeNotifier(ok=False)
    w, site, n, clock = setup([home(1)], notifier=flaky)
    w.tick()
    site.add(home(2))
    clock.advance(minutes=2)
    w.tick()
    assert flaky.sent == []
    flaky.ok = True
    clock.advance(minutes=2)
    w.tick()
    assert flaky.titles() == ["Teststraat 2"]


def test_quiet_hours_hold_messages_and_drop_stale_ones(setup):
    w, site, n, clock = setup([home(1)], notify={"quiet_hours": "09:00-12:00"})
    w.tick()  # 10:00 Amsterdam: quiet, but the welcome is not a listing alert
    site.add(home(2), home(3))
    clock.advance(minutes=2)
    w.tick()
    assert [t for t in n.titles() if t.startswith("Teststraat")] == []
    site.remove(3)
    for _ in range(2):
        clock.advance(minutes=2)
        w.tick()
    clock.advance(hours=2)
    w.tick()
    assert [t for t in n.titles() if t.startswith("Teststraat")] == ["Teststraat 2"]


def test_changing_the_search_does_not_flood(setup, store, make_cfg):
    w, site, n, clock = setup([home(1), home(2, city="Rotterdam")])
    w.tick()
    cfg = make_cfg(search={"cities": ["Eindhoven", "Rotterdam"]})
    w2 = Watcher(cfg, store, client=site, notifier=n, clock=clock)
    clock.advance(minutes=5)
    w2.tick()
    assert n.titles() == ["Watching Codomo", "Search updated"]


def test_existing_homes_on_first_start(setup):
    w, site, n, clock = setup([home(1), home(2)], notify={"existing_on_start": True})
    w.tick()
    assert n.titles() == ["Watching Codomo", "Teststraat 1", "Teststraat 2"]


def test_existing_register_interest_homes_on_first_start(setup):
    w, site, n, clock = setup([home(1), home(2, direct=False, interest=12)], notify={"existing_on_start": True})
    w.tick()
    titles = n.titles()
    assert titles[0] == "Watching Codomo" and "Teststraat 1" in titles and len(titles) == 3
    assert any("12" in body and "shortlist" in body.lower() for _, body in n.sent)
    clock.advance(hours=1)
    w.tick()
    assert len(n.titles()) == 3                    # nothing twice


def test_without_existing_on_start_interest_homes_wait_for_new_ones(setup):
    w, site, n, clock = setup([home(1), home(2, direct=False, interest=12)])
    w.tick()
    assert n.titles() == ["Watching Codomo"]


def test_new_building_is_announced(setup):
    w, site, n, clock = setup([home(1)])
    site.building_pages = ["/homes/nl/en/eindhoven/strijp-t"]
    w.tick()                                  # the first scan only learns what exists
    site.building_pages += ["/homes/nl/en/eindhoven/noordblock", "/homes/nl/en/rotterdam/lex"]
    clock.advance(hours=7)
    w.tick()
    built = [s for s in n.sent if s[0].startswith("New building")]
    assert built == [("New building: Noordblock",
                      "Eindhoven · new on codomo.eu\nhttps://codomo.eu/homes/nl/en/eindhoven/noordblock")]


def test_pause_survives_restart(setup, store, make_cfg):
    w, site, n, clock = setup([home(1)])
    w.tick()
    site.fail = Blocked("blocked")
    clock.advance(minutes=2)
    w.tick()
    site.fail = None
    again = Watcher(make_cfg(), store, client=site, notifier=n, clock=clock)
    before = site.requests
    clock.advance(minutes=1)
    again.tick()
    assert site.requests == before
