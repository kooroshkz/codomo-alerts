from datetime import datetime

from codomo_alerts import messages, schedule
from codomo_alerts.search import Listing

NOW = datetime(2026, 11, 3, 17, 5, tzinfo=schedule.AMS)


def home(name="Kastanjelaan 1-135", **kw):
    data = dict(id="k", name=name, url="https://codomo.eu/homes/nl/en/eindhoven/kastanjelaan/k", price=1998.0,
                status="available", city="Eindhoven", bedrooms=0, contract="indefinite", furnishing="furnished")
    data.update(kw)
    return Listing(**data)


def test_single_alert_is_short():
    title, body = messages.alert("new", home())
    assert title == "Kastanjelaan 1-135"
    assert body == ("Eindhoven · Studio · €1,998\n"
                    "Indefinite · Furnished\n"
                    "https://codomo.eu/homes/nl/en/eindhoven/kastanjelaan/k")


def test_rooms_for_one_gender_say_so():
    _, body = messages.alert("new", home(city="Granada", bedrooms=1, gender="female"))
    assert body.splitlines()[1] == "Indefinite · Furnished · Female only"


def test_digest_lines_say_who_a_room_is_for():
    _, body = messages.digest([("new", home("A", city="Linz", bedrooms=None, gender="male")), ("new", home("B"))])
    assert body.startswith("A · Linz · €1,998 · Male only\n") and "B · Eindhoven · Studio · €1,998\n" in body


def test_missing_details_leave_no_gaps():
    title, body = messages.alert("back", home(city=None, bedrooms=None, contract=None, furnishing=None))
    assert title == "Back: Kastanjelaan 1-135"
    assert body == "€1,998\nhttps://codomo.eu/homes/nl/en/eindhoven/kastanjelaan/k"


def test_price_drop_shows_both_prices():
    _, body = messages.alert("price", home(price=1850.0), "1998")
    assert "€1,998 → €1,850" in body


def test_interest_alert_explains_the_shortlist():
    title, body = messages.alert("interest", home(status="interest", interest=41, contract="6m", bedrooms=2), now=NOW)
    assert title == "Register interest (shortlist): Kastanjelaan 1-135"
    assert "2 bedrooms" in body and "Max 6 months" in body
    assert "41 people showed interest" in body and "Not first come" in body
    assert "1 person showed interest" in messages.alert("interest", home(interest=1))[1]


def test_interest_digest():
    title, body = messages.digest([("interest", home("A", interest=3)), ("interest", home("B"))])
    assert title == "Register interest: 2 homes match" and "3 people showed interest" in body
    assert body.endswith(messages.SHORTLIST)


def test_digest_caps_length():
    items = [("new", home(f"Home {i}", id=str(i))) for i in range(14)]
    title, body = messages.digest(items)
    assert title == "14 new homes"
    assert "and 4 more" in body
    assert body.count("https://") == 10


def test_mixed_digest_labels_each_line():
    title, body = messages.digest([("new", home("A")), ("back", home("B")), ("bookable", home("C"))])
    assert title == "3 homes to look at"
    assert "Back: B" in body and "Now bookable: C" in body


def test_other_messages():
    assert messages.welcome("Eindhoven", 1)[1].startswith("Eindhoven\n1 home matches right now")
    assert messages.building("Noordblock", "Eindhoven", "https://codomo.eu/x") == (
        "New building: Noordblock", "Eindhoven · new on codomo.eu\nhttps://codomo.eu/x")
    assert messages.resumed()[1] == "Codomo answers again."
    assert "14:30" in messages.paused("Cloudflare is blocking automated requests",
                                      datetime(2026, 11, 3, 14, 30, tzinfo=schedule.AMS))[1]
    assert messages.money(1135.5) == "€1,135.50"
