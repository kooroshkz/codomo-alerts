from __future__ import annotations

import gzip
from collections import Counter
from datetime import UTC, datetime, timedelta
from math import ceil
from pathlib import Path

import pytest

from codomo_alerts import catalog
from codomo_alerts.codomo import Card, City, Counts, UnitPage
from codomo_alerts.config import build
from codomo_alerts.store import Store

DATA = Path(__file__).parent / "data"


def page(name: str) -> str:
    """Real codomo.eu pages saved on 2026-11-15: the 2 bedroom list (19 to book directly,
    2 to register interest), a short-stay home and a home with registrations."""
    return gzip.decompress((DATA / name).read_bytes()).decode("utf-8")


def home(n: int, name: str | None = None, *, city: str = "Eindhoven", bedrooms: int | None = 0,
         rent: float = 1100.0,
         extra: float = 100.0, direct: bool = True, furnishing: str = "Furnished", persons: str = "1",
         contract: str = "indefinite", available: str = "2026-12-01", interest: int | None = None,
         country: str = "nl", tags: list[str] | None = None) -> Card:
    key = f"teststraat-{n}"
    slug = catalog.city_slug(catalog.city_label(city))
    card = Card(path=f"/homes/{country}/en/{slug}/test-tower/{key}", country=country, key=key, unit_id=f"uid-{n}",
                name=name or f"Teststraat {n}", city=city, building="Test Tower", bedrooms=bedrooms,
                bedrooms_label=catalog.bedrooms_label(bedrooms), area="40", persons=persons, finishing=furnishing,
                floor="2", available_from=available, min_stay="12 months", rent=rent, extra=extra, direct=direct,
                interest=interest, tags=list(tags or []),
                photos=[f"https://images.codomoliving.com/media/pictures/tst/{key}.jpg"])
    card.contract = contract       # what its own page says
    return card


class FakeCodomo:
    """Answers like codomo.eu: filters, 25 homes a page, page 1 again past the end, counts that
    ignore their own filter, home pages, cities and a sitemap."""

    base_url = "https://codomo.eu"

    def __init__(self, homes: list[Card] | None = None):
        self.db = {h.key: h for h in homes or []}
        self.requests = 0
        self.fail: Exception | None = None
        self.unit_fail: Exception | None = None
        self.calls: list[tuple[str, dict]] = []
        self.units: list[str] = []
        self.city_list = [City(catalog.city_slug(n), n, m.upper()) for n, m in catalog.CITIES.items()]
        self.building_pages: list[str] = []

    def add(self, *homes: Card) -> None:
        for h in homes:
            self.db[h.key] = h

    def remove(self, *numbers: int) -> None:
        for n in numbers:
            self.db.pop(f"teststraat-{n}", None)

    def _hit(self) -> None:
        self.requests += 1
        if self.fail:
            raise self.fail

    def homes(self, country: str, params: dict):
        self._hit()
        self.calls.append((country, dict(params)))
        mode = params.get("publish_mode")
        rows = [h for h in self.db.values() if h.country == country]

        def keep(h: Card, ignore: str = "") -> bool:
            if ignore != "publish_mode" and mode and (mode == "direct_booking") != h.direct:
                return False
            if ignore != "bedrooms" and "bedrooms" in params and h.bedrooms != int(params["bedrooms"]):
                return False
            if "city" in params and catalog.city_slug(catalog.city_label(h.city)) != params["city"]:
                return False
            return not ("max_rent" in params and h.rent > float(params["max_rent"]))

        shown = sorted((h for h in rows if keep(h)), key=lambda h: h.key)
        all_types = [h for h in rows if keep(h, "publish_mode")]
        booking = {None: len(all_types), "direct_booking": sum(h.direct for h in all_types)}
        booking["interest"] = booking[None] - booking["direct_booking"]
        # like the site: homes without a bedroom count (Portugal, Austria) are not in these counts
        bedrooms = dict(Counter(h.bedrooms for h in rows if keep(h, "bedrooms") and h.bedrooms is not None))
        n = int(params.get("page", 1))
        if n > max(1, ceil(len(shown) / 25)):
            n = 1
        return shown[(n - 1) * 25: n * 25], Counts(booking, bedrooms)

    def unit(self, path: str) -> UnitPage:
        self._hit()
        self.units.append(path)
        if self.unit_fail:
            raise self.unit_fail
        h = next(h for h in self.db.values() if h.path == path)
        stay = {"indefinite": "", "2y": "24 months", "1y": "12 months"}.get(h.contract, f"{h.contract[:-1]} months")
        return UnitPage(unit_id=h.unit_id, publish_mode="direct_booking" if h.direct else "interest",
                        interest=h.interest, basic_rent=h.rent, service=h.extra, max_stay=stay,
                        short_stay=h.contract.endswith("m"))

    def cities(self) -> list[City]:
        self._hit()
        return self.city_list

    def photo(self, url: str) -> tuple[int, str]:
        return 200, "image/jpeg"

    def sitemap(self) -> str:
        self._hit()
        locs = "".join(f"<url><loc>https://codomo.eu{p}</loc></url>" for p in self.building_pages)
        return f"<urlset>{locs}</urlset>"


class FakeNotifier:
    def __init__(self, ok: bool = True):
        self.sent: list[tuple[str, str]] = []
        self.ok = ok
        self.invalid: list[str] = []
        self.enabled = True

    def send(self, title, body):
        if self.ok:
            self.sent.append((title, body))
        return self.ok

    def titles(self) -> list[str]:
        return [t for t, _ in self.sent]


class Clock:
    def __init__(self, start: datetime | None = None):
        # a Tuesday at 10:00 in Amsterdam (09:00 UTC in winter time)
        self.now = start or datetime(2026, 11, 3, 9, 0, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, **kw) -> datetime:
        self.now += timedelta(**kw)
        return self.now


@pytest.fixture
def store():
    s = Store(":memory:")
    yield s
    s.close()


@pytest.fixture
def make_cfg(tmp_path):
    def make(search: dict | None = None, notify: dict | None = None, **general):
        raw = {"search": search or {"cities": ["Eindhoven"]}, "notify": notify or {},
               "general": {"data_dir": str(tmp_path), **general}}
        return build(raw, {})
    return make
