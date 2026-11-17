"""MCP server: ask an AI assistant about Codomo homes. Run with `codomo-alerts mcp`."""

from __future__ import annotations

import time

from . import catalog, messages
from .client import Client, CodomoError
from .config import Config, ConfigError, build
from .runtime import db_path
from .search import fetch
from .store import Store, to_listing

CACHE_SECONDS = 60
MAX_RESULTS = 25


def run(cfg: Config) -> None:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise SystemExit("The MCP server needs an extra: pip install 'codomo-alerts[mcp]'") from None

    server = FastMCP("codomo")
    client = Client(cfg.base_url, min_gap=2.0)
    store = Store(db_path(cfg))
    cache: dict[tuple, tuple[float, str]] = {}

    @server.tool()
    def search_homes(city: str = "", bedrooms: str = "", max_price: int = 0, interest: bool = False) -> str:
        """Codomo homes you can book directly right now (or register interest for, with interest=true:
        Codomo then picks someone from the shortlist).

        city: a city name like "Eindhoven" or "The Hague", empty for all of the Netherlands.
        bedrooms: studio, 1, 2, 3, 4 or "2+", empty for any.
        max_price: monthly price in euro with service costs, 0 for no limit.
        """
        key = (city.strip().lower(), bedrooms.strip().lower(), max_price, interest)
        hit = cache.get(key)
        if hit and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        try:
            search = build({"search": {"cities": city or [], "bedrooms": bedrooms or [],
                                       "price_max": max_price or None}}, {}).search
        except ConfigError as e:
            return str(e)
        status = "interest" if interest else "available"
        try:
            found = sorted(fetch(client, search, status).values(),
                           key=lambda x: x.price or 0)[:MAX_RESULTS]
            for x in found:
                store.known_details(x)
        except CodomoError as e:
            return f"Codomo didn't answer: {e}"
        if not found:
            text = "Nothing matches right now."
        else:
            lines = [f"{x.name} · {messages.facts(x)} · {messages.terms(x)}\n{x.url}" for x in found]
            text = "\n\n".join(lines)
            if interest:
                text += f"\n\n{messages.SHORTLIST}"
        cache[key] = (time.monotonic(), text)
        return text

    @server.tool()
    def list_cities() -> str:
        """Cities where Codomo has homes."""
        return ", ".join(catalog.CITIES)

    @server.tool()
    def recent_activity(limit: int = 15) -> str:
        """What the local watcher saw lately: new homes, homes taken, register-interest homes."""
        rows = store.q("""SELECT e.kind, e.at, e.detail, l.* FROM events e JOIN listings l ON l.id = e.listing_id
                          ORDER BY e.id DESC LIMIT ?""", (max(1, min(limit, 100)),))
        if not rows:
            return "No activity recorded. Start the watcher with `codomo-alerts watch` first."
        out = []
        for r in rows:
            x = to_listing(r)
            out.append(f"{r['at'][:16].replace('T', ' ')} UTC  {r['kind']}: {x.name} · {messages.facts(x)}")
        return "\n".join(out)

    server.run()
