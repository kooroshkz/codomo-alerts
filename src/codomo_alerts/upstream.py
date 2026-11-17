"""Does codomo.eu still answer the way this tool expects? Run by maintainers and CI daily.

A failure means alerts are probably broken for everyone. A notice means something new
appeared (a city) that the code should learn about.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import catalog
from .client import Client, CodomoError, Maintenance
from .codomo import contract_key
from .config import Search
from .search import _all, fetch


@dataclass
class Check:
    name: str
    status: str  # ok, fail, notice
    detail: str = ""


def run(client: Client | None = None) -> list[Check]:
    client = client or Client(min_gap=2.0)
    checks: list[Check] = []

    def add(name: str, ok: bool, detail: str = "") -> bool:
        checks.append(Check(name, "ok" if ok else "fail", detail))
        return ok

    try:
        homes, counts = _all(client, "nl", {"publish_mode": "direct_booking"})
    except Maintenance as e:
        add("Homes page answers", False, f"{e} (temporary, try again later)")
        return checks
    except CodomoError as e:
        add("Homes page answers", False, str(e))
        return checks
    add("Homes page answers", True, f"{len(homes)} homes to book directly in the Netherlands")
    if not add("Homes are listed", bool(homes), "" if homes else "0 homes in the whole country is very unusual"):
        return checks

    complete = [c for c in homes if c.rent and c.city and c.bedrooms is not None and c.photos and c.unit_id]
    add("Home cards have the expected fields", len(complete) == len(homes),
        f"{len(homes) - len(complete)} of {len(homes)} incomplete" if len(complete) != len(homes) else "")
    add("Booking counts add up", counts.booking.get(None, 0) >= counts.booking.get("direct_booking", 0) > 0,
        str(counts.booking))

    first = homes[0]
    try:
        page = client.unit(first.path)
        add("Home pages can be read", page.basic_rent is not None,
            f"{first.name}: {catalog.contract_label(contract_key(page))}, rent €{page.basic_rent:,.0f}")
    except CodomoError as e:
        add("Home pages can be read", False, str(e))

    try:
        status, kind = client.photo(first.photos[0])
        add("Photos load", status == 200 and kind.startswith("image/"), f"HTTP {status} {first.photos[0]}")
    except CodomoError as e:
        add("Photos load", False, str(e))

    try:
        two = fetch(client, Search(countries=["nl"], bedrooms=[2]), "available")
        add("Filters are applied", all(x.bedrooms == 2 for x in two.values()), f"{len(two)} homes with 2 bedrooms")
        listed = client.cities()
        unknown = sorted(c.name for c in listed if not any(catalog.same_city(c.name, k) for k in catalog.CITIES))
        if unknown:
            checks.append(Check("New cities", "notice", ", ".join(unknown) + " (add them to catalog.py)"))
    except CodomoError as e:
        add("Follow-up pages answer", False, str(e))
        return checks

    codes = sorted({c.country.lower() for c in listed} - {"nl"}, key=lambda c: (c not in catalog.MARKETS, c))
    for code in codes:
        name = catalog.market_label(code)
        try:
            homes, _ = _all(client, code, {"publish_mode": "direct_booking"})
            add(f"Homes in {name} can be read", True, f"{len(homes)} homes to book directly")
        except CodomoError as e:
            add(f"Homes in {name} can be read", False, str(e))
        if code not in catalog.MARKETS:
            checks.append(Check("New country", "notice", f"{code.upper()} (add it to MARKETS in catalog.py)"))
    return checks


def markdown(checks: list[Check]) -> str:
    icon = {"ok": "✅", "fail": "❌", "notice": "🆕"}
    lines = ["| | Check | Detail |", "|---|---|---|"]
    lines += [f"| {icon[c.status]} | {c.name} | {c.detail} |" for c in checks]
    return "\n".join(lines) + "\n"
