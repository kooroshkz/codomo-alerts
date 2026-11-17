"""The words people read: notification titles and bodies."""

from __future__ import annotations

from datetime import datetime

from . import PROJECT_URL, schedule
from .search import Listing

DIGEST_LIMIT = 10
SHORTLIST = "Not first come: register your interest on codomo.eu, Codomo picks someone from the shortlist"


def money(value: float | None) -> str:
    if value is None:
        return ""
    return f"€{value:,.0f}" if value == int(value) else f"€{value:,.2f}"


def facts(x: Listing) -> str:
    return " · ".join(p for p in (x.city_name, x.bedrooms_name, money(x.price)) if p)


def terms(x: Listing) -> str:
    return " · ".join(p for p in (x.contract_name, x.furnishing_name, x.gender_name) if p)


def interested(x: Listing) -> str:
    if x.interest is None:
        return ""
    return "1 person showed interest" if x.interest == 1 else f"{x.interest} people showed interest"


TITLES = {
    "new": "{name}",
    "back": "Back: {name}",
    "bookable": "Now bookable: {name}",
    "price": "Price drop: {name}",
    "interest": "Register interest (shortlist): {name}",
}


def alert(kind: str, x: Listing, detail: str | None = None, now: datetime | None = None) -> tuple[str, str]:
    lines = [facts(x)]
    if kind == "price" and detail:
        lines = [" · ".join(p for p in (x.city_name, x.bedrooms_name) if p),
                 f"{money(float(detail))} → {money(x.price)}"]
    if terms(x):
        lines.append(terms(x))
    if kind == "interest":
        lines.append(interested(x))
        lines.append(SHORTLIST)
    lines.append(x.url)
    return TITLES[kind].format(name=x.name), "\n".join(line for line in lines if line)


def digest(items: list[tuple[str, Listing]], now: datetime | None = None) -> tuple[str, str]:
    interest = all(kind == "interest" for kind, _ in items)
    n = len(items)
    if interest:
        title = f"Register interest: {n} homes match"
    elif all(kind == "new" for kind, _ in items):
        title = f"{n} new homes"
    else:
        title = f"{n} homes to look at"
    blocks = []
    for kind, x in items[:DIGEST_LIMIT]:
        label = "" if kind in ("new", "interest") else {"back": "Back: ", "bookable": "Now bookable: ",
                                                          "price": "Price drop: "}[kind]
        extra = f" · {interested(x)}" if kind == "interest" and interested(x) else ""
        blocks.append(f"{label}{x.name} · {facts(x)}{extra}\n{x.url}")
    if n > DIGEST_LIMIT:
        blocks.append(f"and {n - DIGEST_LIMIT} more")
    if interest:
        blocks.append(SHORTLIST)
    return title, "\n\n".join(blocks)


def welcome(summary: str, matching: int) -> tuple[str, str]:
    homes = "1 home matches" if matching == 1 else f"{matching} homes match"
    return "Watching Codomo", f"{summary}\n{homes} right now. You'll get a message when a new one shows up."


def search_changed(summary: str, matching: int) -> tuple[str, str]:
    homes = "1 home matches" if matching == 1 else f"{matching} homes match"
    return "Search updated", f"{summary}\n{homes} right now."


def paused(reason: str, until: datetime) -> tuple[str, str]:
    return "Alerts paused", f"{reason}. Trying again at {schedule.local(until):%H:%M}."


def resumed() -> tuple[str, str]:
    return "Alerts back on", "Codomo answers again."


def broken(reason: str) -> tuple[str, str]:
    return "Alerts may be broken", f"{reason}. Check for an update: {PROJECT_URL}/releases"


def building(name: str, city: str, url: str | None = None) -> tuple[str, str]:
    where = " · ".join(p for p in (city, "new on codomo.eu") if p)
    return f"New building: {name}", "\n".join(p for p in (where, url) if p)


def test() -> tuple[str, str]:
    return "codomo-alerts", "Test message. Notifications work."
