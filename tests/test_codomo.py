import json
from datetime import date

import pytest
from conftest import FakeCodomo, home, page

from codomo_alerts import codomo
from codomo_alerts.client import Changed
from codomo_alerts.config import Search
from codomo_alerts.search import _all, building_name, cards, fetch, matches

# ==== reading the real pages


def test_list_page_cards():
    cards, counts = codomo.parse_list(page("list_2_bedrooms.html.gz"))
    assert len(cards) == 21 and counts.booking == {None: 21, "direct_booking": 19, "interest": 2}
    assert counts.bedrooms == {0: 48, 1: 58, 2: 21, 3: 6, 4: 3}
    c = cards[0]
    assert (c.key, c.name, c.city, c.building, c.country) == ("g-h-betzweg-215", "G.H. Betzweg 215", "Rotterdam",
                                                            "The Betz", "nl")
    assert (c.bedrooms, c.area, c.persons, c.finishing, c.floor) == (2, "63.79", "3", "Fully furnished", "4")
    assert (c.available_from, c.min_stay, c.rent, c.extra, c.total) == ("2026-11-17", "1 month", 1811, 298, 2109)
    assert c.direct and c.interest is None and c.unit_id == "6e9c8e12-15c4-4451-a088-8dbf03355bfe"
    assert c.photos[0] == "https://images.codomoliving.com/media/pictures/btz/btz-a2-1.jpg"


def test_every_card_is_complete_and_has_its_own_photos():
    cards, _ = codomo.parse_list(page("list_2_bedrooms.html.gz"))
    for c in cards:
        assert c.bedrooms == 2 and c.rent and c.extra and c.available_from and c.city and c.building, c
    sea = [c for c in cards if c.building == "Sea Tower"]
    assert sea and all("/sea/" in c.photos[0] for c in sea)
    interest = [c for c in cards if not c.direct]
    assert len(interest) == 2 and all(c.interest is not None for c in interest)


def test_unit_pages():
    p = codomo.parse_unit(page("unit_short_stay.html.gz"))
    assert (p.basic_rent, p.service, p.deposit, p.max_stay, p.short_stay) == (1811, 297.53, 2200, "6 months", True)
    assert codomo.contract_key(p) == "6m"
    p = codomo.parse_unit(page("unit_interest.html.gz"))
    assert (p.publish_mode, p.interest, p.max_stay) == ("interest", 116, "")
    assert codomo.contract_key(p) == "indefinite"


@pytest.mark.parametrize("stay,key", [("", "indefinite"), ("24 months", "2y"), ("2 years", "2y"),
                                      ("12 months", "1y"), ("1 year", "1y"), ("4 months", "4m")])
def test_contract_keys(stay, key):
    assert codomo.contract_key(codomo.UnitPage(max_stay=stay)) == key


def test_a_page_without_data_is_a_page_error():
    with pytest.raises(codomo.PageError):
        codomo.parse_list("<html><body>Maintenance</body></html>")
    with pytest.raises(codomo.PageError):
        codomo.parse_unit("<html><body>Maintenance</body></html>")


def test_a_link_without_a_card_is_a_page_error():
    ghost = '<script>self.__next_f.push([1,"zz:{\\"href\\":\\"/homes/nl/en/x/y/ghost\\"}\\n"])</script>'
    with pytest.raises(codomo.PageError, match="links 22 homes, 21 were read"):
        codomo.parse_list(page("list_2_bedrooms.html.gz").replace("</body>", ghost + "</body>"))


def test_reference_loops_do_not_hang():
    rows = '0:["$","div",null,{"children":"$L1"}]\n1:["$","span",null,{"children":["hi","$L1"]}]\n'
    html = "<script>self.__next_f.push([1," + json.dumps(rows) + "])</script>"
    assert codomo.tokens(html)[0] == ["hi"]


def test_cities_and_sitemap_buildings():
    cities = codomo.parse_cities(page("list_2_bedrooms.html.gz"))
    assert {"Amsterdam", "Linz"} <= {c.name for c in cities}
    xml = ("<url><loc>https://codomo.eu/homes/nl/en/eindhoven/noordblock</loc></url>"
           "<url><loc>https://codomo.eu/homes/nl/en/eindhoven/noordblock/unit-1</loc></url>"
           "<url><loc>https://codomo.eu/homes/nl/en/eindhoven</loc></url>")
    assert codomo.parse_buildings(xml) == [("nl", "eindhoven", "noordblock")]
    assert building_name("vb-student-living") == "VB Student Living" and building_name("the-betz") == "The Betz"


# ==== the search: requests, filters and checks against the page's own numbers

class PageClient(FakeCodomo):
    """Answers every list request with a saved page, so the real decoder runs. With
    `booking`, it keeps only the homes of the booking type asked for, like the site."""

    def __init__(self, html: str, booking: bool = True):
        super().__init__()
        self.html = html
        self.booking = booking

    def homes(self, country, params):
        self._hit()
        self.calls.append((country, dict(params)))
        found, counts = codomo.parse_list(self.html)
        mode = params.get("publish_mode")
        if self.booking and mode:
            found = [c for c in found if c.direct == (mode == "direct_booking")]
        return found, counts


def test_fetch_reads_a_real_page():
    client = PageClient(page("list_2_bedrooms.html.gz"))
    got = fetch(client, Search(bedrooms=[2], price_max=2500), "available")
    assert client.calls == [("nl", {"publish_mode": "direct_booking", "max_rent": "2500", "bedrooms": "2"})]
    assert "g-h-betzweg-215" in got and got["g-h-betzweg-215"].price == 2109


def test_the_wrong_booking_type_is_an_error():
    # the saved page has both kinds: a site that ignores the booking type must be noticed
    with pytest.raises(Changed):
        fetch(PageClient(page("list_2_bedrooms.html.gz"), booking=False), Search(bedrooms=[2]), "available")
    interest = fetch(PageClient(page("list_2_bedrooms.html.gz")), Search(bedrooms=[2]), "interest")
    assert len(interest) == 2 and all(x.status == "interest" and x.interest is not None for x in interest.values())


def edit_count(label: str, old: int, new: int) -> str:
    html = page("list_2_bedrooms.html.gz")
    out = html.replace(f'{label}\\",\\"count\\":{old}', f'{label}\\",\\"count\\":{new}')
    assert out != html
    return out


def test_fewer_homes_than_counted_is_normal_more_or_far_fewer_is_not():
    # the site counts a few homes it never shows (155 counted, 144 shown on 2026-11-16)
    assert len(_all(PageClient(edit_count("All homes", 21, 24)), "nl", {})[0]) == 21
    with pytest.raises(Changed, match="says 20 homes, 21 were read"):
        _all(PageClient(edit_count("All homes", 21, 20)), "nl", {})
    with pytest.raises(Changed, match="says 50 homes"):
        _all(PageClient(edit_count("All homes", 21, 50)), "nl", {})


def test_paging_stops_when_a_page_past_the_end_shows_page_one_again():
    client = FakeCodomo([home(i) for i in range(30)])
    homes, _ = _all(client, "nl", {})
    assert len(homes) == 30 and [c[1].get("page") for c in client.calls] == [None, "2"]
    client = FakeCodomo([home(i) for i in range(25)])
    assert len(_all(client, "nl", {})[0]) == 25 and len(client.calls) == 2


def test_one_request_per_bedroom_count_with_homes():
    client = FakeCodomo([home(1, bedrooms=2), home(2, bedrooms=3), home(3, bedrooms=0)])
    got = fetch(client, Search(bedrooms=[2, 3, 4]), "available")
    assert set(got) == {"teststraat-1", "teststraat-2"}
    assert [c[1]["bedrooms"] for c in client.calls] == ["2", "3"]      # 4 has no homes: not asked


def test_an_ignored_bedroom_filter_is_an_error():
    with pytest.raises(Changed, match="ignored the bedroom filter"):
        cards(PageClient(page("list_2_bedrooms.html.gz")), "nl", {}, [3])


def test_one_city_goes_in_the_url():
    client = FakeCodomo([home(1, city="Den Haag"), home(2, city="Rotterdam")])
    got = fetch(client, Search(cities=["The Hague"]), "available")
    assert list(got) == ["teststraat-1"] and client.calls[0][1]["city"] == "den-haag"


def search(**kw):
    return Search(**{"bedrooms": [2, 3], "price_max": 2500, "furnishing": ["furnished", "semi-furnished"],
                     "exclude_cities": ["Eindhoven"], **kw})


@pytest.mark.parametrize("card,result", [
    (home(1, bedrooms=2, city="Rotterdam"), True),
    (home(2, bedrooms=2, city="Eindhoven"), False),                       # excluded
    (home(3, bedrooms=2, city="Rotterdam", furnishing="Unfurnished"), False),
    (home(4, bedrooms=2, city="Rotterdam", rent=2450, extra=100), False),  # total 2550
    (home(5, bedrooms=2, city="Linz", country="at"), False),               # Netherlands only
    (home(6, bedrooms=4, city="Rotterdam"), None),                         # the site should have filtered it
])
def test_filters_on_our_side(card, result):
    assert matches(search(), card) is result


def test_city_aliases_persons_and_move_in():
    assert matches(search(cities=["The Hague"], exclude_cities=[]), home(1, bedrooms=2, city="Den Haag"))
    assert not matches(search(persons=3), home(1, bedrooms=2, city="Rotterdam", persons="2"))
    assert not matches(search(move_in_before=date(2026, 11, 20)), home(1, bedrooms=2, city="Rotterdam"))
    assert matches(search(cities=["Linz"], exclude_cities=[]), home(1, bedrooms=2, city="Linz", country="at"))


def test_cities_abroad_are_read_only_when_named():
    assert Search().markets() == ["nl"]
    assert Search(cities=["Linz", "Rotterdam"]).markets() == ["at", "nl"]
