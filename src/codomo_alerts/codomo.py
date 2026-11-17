"""Reading codomo.eu pages.

codomo.eu (formerly Holland2Stay) renders its pages on the server with Next.js.
The data of a page sits in its React Server Components payload: strings pushed with
``self.__next_f.push([1, "..."])``. Joined, they are rows ``<hex id>:<payload>``; a
``"$L<id>"`` or ``"$<id>"`` inside a row stands for another row. Walking the tree from
row ``0`` gives the page text in reading order. The visible HTML is streamed in pieces
out of order, so reading it directly pairs prices with the wrong homes.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime

PUSH = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', re.S)
# $<id> a row, $L<id> a lazy row, $@<id> a streamed (promise) row, $Q<id> a Map in a row
REF = re.compile(r"\$[L@Q]?([0-9a-f]+)((?::[A-Za-z0-9_]+)*)")
REF_IN_DATA = re.compile(r'"\$[L@Q]?([0-9a-f]+)[":]')
UNIT_PATH = re.compile(r"^/homes/([a-z]{2})/[a-z]{2}/[a-z0-9-]+/[a-z0-9-]+/([a-z0-9-]+)$")
LINK_IN_DATA = re.compile(r'"href":"(/homes/[a-z]{2}/[a-z]{2}/[a-z0-9-]+/[a-z0-9-]+/[a-z0-9-]+)"')
SKIP_TAGS = {"script", "style", "svg", "path", "circle", "link", "meta", "noscript", "template"}
FURNISHING_LABELS = {"fully furnished", "furnished", "semi furnished", "semi-furnished", "unfurnished"}
MAX_NODES = 400_000


class PageError(ValueError):
    """The page does not look like we expect: the site changed."""


def payload(html: str) -> str:
    parts = PUSH.findall(html)
    if not parts:
        raise PageError("no Next.js data in the page")
    try:
        return "".join(json.loads('"' + p + '"') for p in parts)
    except ValueError as e:
        raise PageError(f"unreadable Next.js data: {e}") from e


def parse_rows(data: str) -> dict[str, object]:
    """Rows by id. JSON rows are parsed, ``T`` rows are text, others (module refs) are None."""
    b = data.encode("utf-8")
    out: dict[str, object] = {}
    i, n = 0, len(b)
    while i < n:
        colon = b.find(b":", i)
        if colon < 0:
            break
        rid = b[i:colon].decode("utf-8", "replace")
        if not re.fullmatch(r"[0-9a-f]+", rid):
            nl = b.find(b"\n", i)
            i = n if nl < 0 else nl + 1
            continue
        j = colon + 1
        if b[j:j + 1] == b"T":                 # T<hex byte length>,<text>
            comma = b.find(b",", j)
            try:
                length = int(b[j + 1:comma], 16)
            except ValueError:
                raise PageError(f"bad text row {rid}") from None
            out[rid] = b[comma + 1:comma + 1 + length].decode("utf-8", "replace")
            i = comma + 1 + length
            continue
        nl = b.find(b"\n", j)
        nl = n if nl < 0 else nl
        text = b[j:nl].decode("utf-8", "replace")
        if text[:1] in '[{"' or text[:1].isdigit() or text in ("null", "true", "false"):
            try:
                out[rid] = json.loads(text)
            except ValueError:
                out[rid] = None
        else:
            out[rid] = None
        i = nl + 1
    return out


class _Walker:
    """Page text in reading order, plus markers for links, unit ids and photo lists."""

    def __init__(self, rows: dict[str, object]):
        self.rows = rows
        self.out: list[object] = []
        self.nodes = 0
        self.active: set[str] = set()       # rows being expanded: a reference back is a loop

    def deref(self, v, depth=0):
        """Follow a "$<id>[:path]" reference to its value; anything else is returned as is."""
        if not (isinstance(v, str) and v.startswith("$") and len(v) > 1):
            return v, None
        m = REF.fullmatch(v)
        if not m or m.group(1) not in self.rows or depth > 50:
            return None, None
        x = self.rows[m.group(1)]
        for part in [p for p in m.group(2).split(":") if p]:
            x, _ = self.deref(x, depth + 1)
            if isinstance(x, list) and part.isdigit():
                x = x[int(part)] if int(part) < len(x) else None
            elif isinstance(x, dict):
                x = x.get(part)
            else:
                x = None
        if m.group(2):
            x, _ = self.deref(x, depth + 1)
        return x, m.group(1)

    def walk(self, v, text: bool) -> None:
        """``text``: strings here are page text (an element's children), not prop values."""
        self.nodes += 1
        if self.nodes > MAX_NODES:
            raise PageError("page data too large")
        v, rid = self.deref(v)
        if rid is not None:
            if rid in self.active:
                return
            self.active.add(rid)
            try:
                self._walk(v, text)
            finally:
                self.active.discard(rid)
        else:
            self._walk(v, text)

    def _walk(self, v, text: bool) -> None:
        if v is None or isinstance(v, bool):
            return
        if isinstance(v, str):
            if text and v.strip() and not v.startswith("$"):
                self.out.append(v)
            return
        if isinstance(v, (int, float)):
            if text:
                self.out.append(str(v))
            return
        if isinstance(v, dict):
            for x in v.values():
                if isinstance(x, (list, dict)) or isinstance(x, str) and x.startswith("$"):
                    self.walk(x, False)
            return
        if not isinstance(v, list):
            return
        if len(v) == 4 and v[0] == "$" and isinstance(v[3], dict):     # a React element
            tag, props = v[1], v[3]
            if isinstance(tag, str) and tag in SKIP_TAGS or "dangerouslySetInnerHTML" in props:
                return
            href = props.get("href")
            if isinstance(href, str):
                self.out.append({"href": href})
            if isinstance(props.get("unitId"), str):
                self.out.append({"unitId": props["unitId"]})
            if "photos" in props:
                photos, _ = self.deref(props["photos"])
                if isinstance(photos, list):
                    urls = []
                    for p in photos:
                        p, _ = self.deref(p)
                        if isinstance(p, dict) and isinstance(p.get("url"), str):
                            urls.append(p["url"])
                    self.out.append({"photos": urls})
            self.walk(props.get("children"), True)
            # other props can carry elements too (slots of client components)
            for k, x in props.items():
                if k != "children" and (isinstance(x, list) and x[:1] == ["$"] or isinstance(x, str)
                                        and REF.fullmatch(x) and x.startswith("$L")):
                    self.walk(x, True)
            return
        for x in v:
            self.walk(x, text)


def tokens(html: str) -> tuple[list[object], str]:
    """The page as a list of text strings and marker dicts, and its raw data. Starts from
    every row no other row refers to, in page order."""
    data = payload(html)
    rows = parse_rows(data)
    if not rows:
        raise PageError("no rows in the page data")
    referenced = set(REF_IN_DATA.findall(data))
    w = _Walker(rows)
    for rid in [r for r in rows if r not in referenced]:
        w.active.add(rid)
        w._walk(rows[rid], False)
        w.active.discard(rid)
    return w.out, data


# ============================================================ list page

@dataclass
class Card:
    path: str                     # /homes/nl/en/rotterdam/the-betz/g-h-betzweg-215
    country: str
    key: str                      # last part of the path
    unit_id: str = ""
    name: str = ""
    city: str = ""
    building: str = ""
    bedrooms: int | None = None   # 0 = studio or loft
    bedrooms_label: str = ""
    area: str = ""
    persons: str = ""
    finishing: str = ""
    floor: str = ""
    available_from: str = ""      # YYYY-MM-DD
    min_stay: str = ""            # "12 months"
    rent: float | None = None     # rent shown on the card, without service costs
    extra: float | None = None    # "Excl. €298/month for service costs ..."
    direct: bool = False          # "Book directly"
    interest: int | None = None   # "26 people have shown interest in this home"
    tags: list[str] = field(default_factory=list)
    photos: list[str] = field(default_factory=list)

    @property
    def total(self) -> float | None:
        if self.rent is None:
            return None
        return self.rent + (self.extra or 0)


def money(text: str) -> float | None:
    m = re.search(r"€\s?(\d[\d,]*(?:\.\d+)?)", text or "")
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def iso_day(text: str) -> str:
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(text.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


BEDROOMS_RE = re.compile(r"^(studio|loft.*|(\d+) bedrooms?)$", re.I)
PERSONS_RE = re.compile(r"^(\d+) persons?$", re.I)
FLOOR_RE = re.compile(r"^(-?\d+)\. floor$", re.I)
DATE_RE = re.compile(r"^[A-Z][a-z]{2,8} \d{1,2}, \d{4}$")
MIN_STAY_RE = re.compile(r"^Min\.? (\d+ (?:months?|years?))$", re.I)
INTEREST_RE = re.compile(r"^(\d+) (?:people have|person has) shown interest", re.I)
NUMBER_RE = re.compile(r"^\d+(?:[.,]\d+)?$")


def _fill(card: Card, texts: list[str]) -> None:
    """Card fields from its text, first occurrence wins (cards repeat their features)."""
    if texts:
        title = texts[0]
        if ", " in title:
            card.name, card.city = title.rsplit(", ", 1)
        else:
            card.name = title
    floor_at = None
    for i, t in enumerate(texts[1:], 1):
        s = t.strip()
        if card.bedrooms is None and (m := BEDROOMS_RE.match(s)):
            card.bedrooms_label = s
            card.bedrooms = int(m.group(2)) if m.group(2) else 0
        elif not card.area and NUMBER_RE.match(s) and i + 1 < len(texts) and texts[i + 1].strip() == "m":
            card.area = s.replace(",", ".")
        elif not card.persons and (m := PERSONS_RE.match(s)):
            card.persons = m.group(1)
        elif not card.finishing and " ".join(s.lower().split()) in FURNISHING_LABELS:
            card.finishing = s
        elif not card.floor and (m := FLOOR_RE.match(s)):
            card.floor, floor_at = m.group(1), i
        elif floor_at is not None and i == floor_at + 1 and not card.building and not DATE_RE.match(s):
            card.building = s
        elif not card.available_from and DATE_RE.match(s):
            card.available_from = iso_day(s)
        elif not card.min_stay and (m := MIN_STAY_RE.match(s)):
            card.min_stay = m.group(1)
        elif card.rent is None and re.fullmatch(r"€\s?[\d.,]+", s):
            card.rent = money(s)
        elif card.extra is None and s.startswith("*Excl."):
            card.extra = money(s)
        elif s == "Book directly":
            card.direct = True
        elif card.interest is None and (m := INTEREST_RE.match(s)):
            card.interest = int(m.group(1))
        elif s.lower().endswith(" only") and len(s) < 40 and s not in card.tags:
            card.tags.append(s)


@dataclass
class Counts:
    """The page's own numbers for the current filters. Like most shops, the site counts
    each option of a filter as if that one filter were not set."""
    booking: dict[str | None, int]      # {None: all, "direct_booking": n, "interest": n}
    bedrooms: dict[int, int]            # {0: studios, 1: n, 2: n, ...}


def list_counts(data: str) -> Counts:
    m = re.search(r'"options":\{"booking_type":', data)
    if not m:
        raise PageError("no filter counts in the page")
    try:
        options, _ = json.JSONDecoder().raw_decode(data, m.start() + len('"options":'))
        booking = {o.get("value"): int(o.get("count") or 0) for o in options["booking_type"]}
        bedrooms = {int(o["value"]): int(o.get("count") or 0) for o in options.get("bedrooms") or []
                    if isinstance(o.get("value"), int)}
    except (ValueError, TypeError, AttributeError, KeyError) as e:
        raise PageError(f"unreadable filter counts: {e}") from e
    if None not in booking:
        raise PageError("no total in the filter counts")
    return Counts(booking, bedrooms)


def parse_list(html: str) -> tuple[list[Card], Counts]:
    """The home cards of a list page and the page's numbers. A country without homes
    shows homes of other countries instead; ``Card.country`` tells them apart."""
    toks, data = tokens(html)
    counts = list_counts(data)
    cards: list[Card] = []
    texts: dict[str, list[str]] = {}
    seen: set[str] = set()
    cur: Card | None = None
    pending_photos: list[str] = []
    for t in toks:
        if isinstance(t, dict):
            href = t.get("href")
            if isinstance(href, str) and (m := UNIT_PATH.match(href.split("?")[0])):
                path = href.split("?")[0]
                if cur is not None and path == cur.path:
                    continue
                if path in seen:
                    cur = None          # the same home again further down: not a new card
                    continue
                seen.add(path)
                cur = Card(path=path, country=m.group(1), key=m.group(2), photos=pending_photos)
                pending_photos = []
                cards.append(cur)
                texts[path] = []
            elif "photos" in t:
                # the photo carousel comes just before the card's title
                pending_photos = [u for u in t["photos"] if "/media/" in u]
            elif "unitId" in t and cur is not None and not cur.unit_id:
                cur.unit_id = t["unitId"]
            continue
        if cur is not None:
            texts[cur.path].append(t)
    for c in cards:
        _fill(c, texts[c.path])
    # every home the page links to must be a card we read: a layout change shows here,
    # independent of the site's own numbers
    linked = set(LINK_IN_DATA.findall(data))
    if linked != {c.path for c in cards}:
        raise PageError(f"the page links {len(linked)} homes, {len(cards)} were read")
    return cards, counts


# ============================================================ unit page

@dataclass
class UnitPage:
    """The price widget of a home's own page, which gets the home's data as props."""
    unit_id: str = ""
    publish_mode: str = ""        # direct_booking or interest
    interest: int | None = None
    basic_rent: float | None = None
    service: float | None = None  # service costs and facilities per month
    deposit: float | None = None
    available_from: str = ""      # YYYY-MM-DD
    min_stay: str = ""            # "12 months"
    max_stay: str = ""            # "6 months"; empty means no maximum
    short_stay: bool = False
    audience: list[str] = field(default_factory=list)    # student, employed
    gender: str = ""

    @property
    def total(self) -> float | None:
        if self.basic_rent is None:
            return None
        return self.basic_rent + (self.service or 0)


def _num(v) -> float | None:
    try:
        return None if v is None or isinstance(v, bool) else float(v)
    except (TypeError, ValueError):
        return None


def parse_unit(html: str) -> UnitPage:
    rows = parse_rows(payload(html))
    found: list[dict] = []

    def scan(v, depth=0):
        if depth > 60 or found:
            return
        if isinstance(v, list):
            if len(v) == 4 and v[0] == "$" and isinstance(v[3], dict) and "basicRent" in v[3] and "unitId" in v[3]:
                found.append(v[3])
                return
            for x in v:
                scan(x, depth + 1)
        elif isinstance(v, dict):
            for x in v.values():
                scan(x, depth + 1)
    for r in rows.values():
        scan(r)
    if not found:
        raise PageError("no price details on the unit page")
    p = found[0]
    stay = p.get("maxTerm")
    page = UnitPage(
        unit_id=str(p.get("unitId") or ""), publish_mode=str(p.get("publishMode") or ""),
        interest=int(p["interestCount"]) if isinstance(p.get("interestCount"), (int, float)) else None,
        basic_rent=_num(p.get("basicRent")), service=_num(p.get("serviceCharge")), deposit=_num(p.get("deposit")),
        available_from=str(p.get("availableFromDisplay") or "")[:10],
        min_stay=str(p.get("minimumStay") or ""), max_stay=stay if isinstance(stay, str) else "",
        short_stay=bool(p.get("shortStay")),
        audience=[str(a) for a in p.get("audience") or [] if isinstance(a, str)],
        gender=str(p.get("genderRestriction") or ""))
    if page.basic_rent is None:
        raise PageError("unit page without a rent")
    return page


def months(text: str) -> int | None:
    """``"6 months"`` -> 6, ``"1 year"`` -> 12."""
    m = re.match(r"(\d+)\s*(month|year)", (text or "").strip().lower())
    if not m:
        return None
    return int(m.group(1)) * (12 if m.group(2) == "year" else 1)


def contract_key(page: UnitPage) -> str:
    """The longest stay a home allows: indefinite, 2y, 1y, or <n>m for shorter maximums."""
    top = months(page.max_stay)
    if top is None:
        return "indefinite"
    if top >= 24:
        return "2y"
    if top >= 12:
        return "1y"
    return f"{top}m"


def contract_label(page: UnitPage) -> str:
    if not page.max_stay:
        return "No maximum stay"
    return f"Max {page.max_stay}" + (" (short stay)" if page.short_stay else "")


# ============================================================ cities

@dataclass
class City:
    slug: str
    name: str
    country: str          # NL, AT, ES, PT


def parse_cities(html: str) -> list[City]:
    """The cities codomo.eu lists in its menus, from any page."""
    data = payload(html)
    m = re.search(r'"cities":\[\{"slug"', data)
    if not m:
        raise PageError("no city list in the page")
    try:
        items, _ = json.JSONDecoder().raw_decode(data, m.start() + len('"cities":'))
        return [City(str(c["slug"]), str(c["name"]), str(c.get("country") or "")) for c in items]
    except (ValueError, TypeError, KeyError) as e:
        raise PageError(f"unreadable city list: {e}") from e


# ============================================================ sitemap

BUILDING_URL = re.compile(r"<loc>https://codomo\.eu/homes/([a-z]{2})/en/([a-z0-9-]+)/([a-z0-9-]+)</loc>")


def parse_buildings(sitemap: str) -> list[tuple[str, str, str]]:
    """(country, city slug, building slug) of every building page in the sitemap."""
    return list(dict.fromkeys(BUILDING_URL.findall(sitemap)))
