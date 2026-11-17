"""Turn a Search into list page requests and the home cards into Listings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

from . import catalog
from .client import Changed, Client, CodomoError
from .codomo import Card, Counts, contract_key, parse_buildings
from .config import Search

log = logging.getLogger("codomo_alerts")

PAGE_SIZE = 25      # homes per list page
MAX_PAGES = 10


@dataclass
class Listing:
    id: str                     # the last part of the home's address, e.g. g-h-betzweg-215
    name: str
    url: str
    price: float | None         # per month, service costs included
    status: str                 # available (book directly) or interest (register interest)
    city: str | None = None
    bedrooms: int | None = None
    contract: str | None = None
    furnishing: str | None = None
    building: str | None = None
    persons: int | None = None
    available_from: str | None = None
    interest: int | None = None  # people who registered interest so far

    @property
    def city_name(self) -> str:
        return catalog.city_label(self.city)

    @property
    def bedrooms_name(self) -> str:
        return catalog.bedrooms_label(self.bedrooms)

    @property
    def contract_name(self) -> str:
        return catalog.contract_label(self.contract)

    @property
    def furnishing_name(self) -> str:
        return catalog.FURNISHING.get(self.furnishing or "", "")


def to_listing(card: Card, base_url: str) -> Listing:
    return Listing(
        id=card.key, name=card.name or card.key, url=f"{base_url}{card.path}", price=card.total,
        status="available" if card.direct else "interest", city=catalog.city_label(card.city) or None,
        bedrooms=card.bedrooms, furnishing=catalog.furnishing_of(card.finishing),
        building=card.building or None, persons=int(card.persons) if card.persons.isdigit() else None,
        available_from=card.available_from or None, interest=card.interest)


def matches(search: Search, card: Card) -> bool | None:
    """Every filter, checked on our side. None: the home fails a filter the site should have
    applied (bedrooms), so the answer looks wrong."""
    if search.bedrooms and card.bedrooms is not None and card.bedrooms not in search.bedrooms:
        return None
    if search.cities and not any(catalog.same_city(card.city, c) for c in search.cities):
        return False
    if not search.cities and card.country != "nl":
        return False
    if any(catalog.same_city(card.city, c) for c in search.exclude_cities):
        return False
    if search.furnishing and catalog.furnishing_of(card.finishing) not in search.furnishing:
        return False
    total = card.total
    if total is not None and (search.price_min and total < search.price_min
                              or search.price_max and total > search.price_max):
        return False
    if search.persons and card.persons.isdigit() and int(card.persons) < search.persons:
        return False
    late = bool(search.move_in_before and card.available_from
                and date.fromisoformat(card.available_from) > search.move_in_before)
    return not late


def _all(client: Client, country: str, params: dict[str, str]) -> tuple[list[Card], Counts]:
    """Every home of one country for these filters, over all pages. Raises Changed when the
    homes read do not fit the page's own numbers.

    The site counts a few homes it never shows (2026-11-16: 155 counted, 144 on the pages), so
    fewer homes than counted is normal. More than counted, far fewer, or the wrong booking type
    means the page was misread. A page past the end shows page 1 again, so a page with nothing
    new ends the list."""
    mode = params.get("publish_mode")
    found: dict[str, Card] = {}
    others = 0
    counts = Counts({None: 0}, {})
    for page in range(1, MAX_PAGES + 1):
        p = dict(params)
        if page > 1:
            p["page"] = str(page)
        cards, counts = client.homes(country, p)
        new = 0
        for c in cards:
            if c.country != country:
                others += 1
            elif c.path not in found:
                found[c.path] = c
                new += 1
        if others and not found:
            return [], counts       # "no homes in this country yet, here are homes elsewhere"
        if len(cards) < PAGE_SIZE or new == 0:
            break
    else:
        raise Changed(f"More than {MAX_PAGES} pages of homes: a filter is probably ignored")
    homes = list(found.values())
    expected = counts.booking.get(mode)
    if expected is None:
        raise Changed("Codomo's homes page has no total")
    if len(homes) > expected or expected >= 4 and len(homes) < expected / 2:
        raise Changed(f"Codomo's homes page says {expected} homes, {len(homes)} were read")
    direct = sum(c.direct for c in homes)
    if mode == "direct_booking" and direct != len(homes) or mode == "interest" and direct:
        raise Changed(f"Codomo sent homes of the wrong kind (asked for {mode})")
    if mode is None and (direct > counts.booking.get("direct_booking", direct)
                         or len(homes) - direct > counts.booking.get("interest", len(homes))):
        raise Changed("Codomo's booking counts do not match its homes")
    return homes, counts


def cards(client: Client, country: str, params: dict[str, str], bedrooms: list[int]) -> list[Card]:
    """One request per bedroom count that has homes (the site filters one count at a time)."""
    if not bedrooms:
        return _all(client, country, params)[0]

    def one(n: int) -> tuple[list[Card], Counts]:
        homes, counts = _all(client, country, {**params, "bedrooms": str(n)})
        wrong = [c for c in homes if c.bedrooms is not None and c.bedrooms != n]
        if wrong:
            raise Changed(f"Codomo ignored the bedroom filter (asked for {n}, got {wrong[0].bedrooms_label})")
        return homes, counts

    homes, counts = one(bedrooms[0])
    for n, count in sorted(counts.bedrooms.items()):
        if n in bedrooms[1:] and count > 0:
            homes += one(n)[0]
    return homes


def fetch(client: Client, search: Search, status: str) -> dict[str, Listing]:
    """Every home that matches the search right now, by its key."""
    params = {"publish_mode": catalog.STATUS[status]}
    if search.price_max:
        # the site filters on the rent without service costs, so this keeps every home whose
        # total fits; the total is checked in matches()
        params["max_rent"] = str(search.price_max)
    if len(search.cities) == 1:
        params["city"] = catalog.city_slug(search.cities[0])
    out: dict[str, Listing] = {}
    odd = 0
    for country in search.markets():
        for card in cards(client, country, params, search.bedrooms):
            ok = matches(search, card)
            if ok is None:
                odd += 1
            elif ok:
                out[card.key] = to_listing(card, client.base_url)
    if odd and not out:
        raise Changed(f"All {odd} homes Codomo sent fail filters it should have applied")
    if odd:
        log.warning("Codomo sent %d homes that do not match the filters it applied; ignored them", odd)
    return out


def contract(client: Client, listing: Listing) -> str | None:
    """The longest stay a home allows, read from its own page. None when the page can't be
    read; a block, rate limit or maintenance is raised so the watcher backs off."""
    try:
        page = client.unit(listing.url.removeprefix(client.base_url))
    except CodomoError as e:
        if e.kind in ("blocked", "rate_limited", "maintenance"):
            raise
        log.info("Couldn't read the page of %s: %s", listing.name, e)
        return None
    return contract_key(page)


def discover_cities(client: Client) -> dict[str, str]:
    """Cities codomo.eu lists right now: name -> country code."""
    return {c.name: c.country.lower() for c in client.cities()}


def buildings(client: Client) -> list[tuple[str, str, str]]:
    """(country, city slug, building slug) of every building page in the sitemap."""
    return parse_buildings(client.sitemap())


def building_name(slug: str) -> str:
    """'the-betz' -> 'The Betz', 'vb-student-living' -> 'VB Student Living'."""
    return " ".join(w.upper() if len(w) <= 2 and w not in ("de", "op", "of", "in") else w.capitalize()
                    for w in slug.split("-"))
