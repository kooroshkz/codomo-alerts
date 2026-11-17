import pytest
import requests
from conftest import page

from codomo_alerts import USER_AGENT
from codomo_alerts.client import Blocked, Changed, Client, Maintenance, RateLimited, Unavailable


class Resp:
    def __init__(self, status=200, text="", headers=None):
        self.status_code = status
        self.text = text
        self.content = text.encode()
        self.headers = headers or {}


class Session:
    def __init__(self, resp=None, error=None):
        self.resp, self.error = resp or Resp(), error
        self.headers = {}
        self.calls = []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        if self.error:
            raise self.error
        return self.resp


def client(resp=None, error=None) -> Client:
    return Client(min_gap=0, session=Session(resp, error))


def test_identifies_itself_and_does_not_follow_redirects():
    c = client(Resp(200, "<html>"))
    assert c.get("/homes/nl/en", {"bedrooms": "2"}) == "<html>"
    url, kw = c.session.calls[0]
    assert url == "https://codomo.eu/homes/nl/en" and kw["params"] == {"bedrooms": "2"}
    assert kw["allow_redirects"] is False
    assert c.session.headers["User-Agent"] == USER_AGENT and "Referer" not in c.session.headers
    assert "codomo-alerts" in USER_AGENT


@pytest.mark.parametrize("resp,error", [
    (Resp(429, headers={"Retry-After": "30"}), RateLimited),
    (Resp(403, "<title>Just a moment...</title>", {"cf-mitigated": "challenge"}), Blocked),
    (Resp(403, "no"), Blocked),
    (Resp(302, headers={"Location": "https://codomo-maintenance.pages.dev/"}), Maintenance),
    (Resp(503, "<h1>We are doing maintenance</h1>"), Maintenance),
    (Resp(301, headers={"Location": "https://elsewhere.example/"}), Changed),
    (Resp(404), Changed),
    (Resp(502, "bad gateway"), Unavailable),
])
def test_errors_are_classified(resp, error):
    with pytest.raises(error):
        client(resp).get("/homes/nl/en")


def test_maintenance_is_temporary_not_a_change():
    assert issubclass(Maintenance, Unavailable) and not issubclass(Maintenance, Changed)


def test_retry_after_is_read():
    with pytest.raises(RateLimited) as e:
        client(Resp(429, headers={"Retry-After": "120"})).get("/")
    assert e.value.retry_after == 120


def test_network_errors_are_unavailable():
    with pytest.raises(Unavailable):
        client(error=requests.ConnectionError("down")).get("/")


def test_a_page_the_parser_does_not_understand_is_a_change():
    with pytest.raises(Changed, match="changed its homes page"):
        client(Resp(200, "<html>Coming soon</html>")).homes("nl", {})


def test_homes_and_unit_pages():
    cards, counts = client(Resp(200, page("list_2_bedrooms.html.gz"))).homes("nl", {"bedrooms": "2"})
    assert len(cards) == 21 and counts.booking[None] == 21
    unit = client(Resp(200, page("unit_short_stay.html.gz"))).unit("/homes/nl/en/rotterdam/the-betz/g-h-betzweg-215")
    assert unit.max_stay == "6 months" and unit.basic_rent == 1811
