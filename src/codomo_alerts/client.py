"""Small client for the public codomo.eu pages.

codomo.eu has no public API: the list of homes is rendered on the server, and the data
sits in the page (see codomo.py). The client says who it is in the User-Agent, sends one
request at a time, keeps a gap between requests and never pretends to be a browser.
"""

from __future__ import annotations

import math
import threading
import time
from email.utils import parsedate_to_datetime

import requests

from . import USER_AGENT, codomo
from .config import DEFAULT_BASE_URL


class CodomoError(Exception):
    kind = "error"


class Blocked(CodomoError):
    kind = "blocked"


class RateLimited(CodomoError):
    kind = "rate_limited"

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class Unavailable(CodomoError):
    kind = "unavailable"


class Maintenance(Unavailable):
    """Codomo shows its maintenance page (2026-11-16 23:01 to 23:31 every page redirected to
    codomo-maintenance.pages.dev). Temporary: nothing to update."""
    kind = "maintenance"


class Changed(CodomoError):
    kind = "changed"


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
        return max(0.0, seconds) if math.isfinite(seconds) else None
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
    except (TypeError, ValueError):
        return None


class Client:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, min_gap: float = 2.0, timeout: float = 30,
                 session: requests.Session | None = None):
        self.base_url = base_url.rstrip("/")
        self.min_gap = min_gap
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8",
                                     "Accept-Language": "en"})
        self._lock = threading.Lock()
        self._last = 0.0
        self.requests = 0
        self.bytes = 0

    def get(self, path: str, params: dict | list | None = None) -> str:
        with self._lock:
            wait = self.min_gap - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            try:
                # redirects are not followed: a moved site must show as a change, not as an odd page
                r = self.session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout,
                                     allow_redirects=False)
            except requests.RequestException as e:
                raise Unavailable(f"Can't reach Codomo ({type(e).__name__})") from None
            finally:
                self._last = time.monotonic()
                self.requests += 1
        self.bytes += len(r.content or b"")
        return self._parse(r)

    @staticmethod
    def _parse(r) -> str:
        status = r.status_code
        text = r.text if r.content else ""
        location = r.headers.get("Location") or ""
        if status == 429:
            raise RateLimited("Codomo asked us to slow down", _retry_after(r.headers.get("Retry-After")))
        if status in (403, 503) and (r.headers.get("cf-mitigated") or "Just a moment" in text[:2000]):
            raise Blocked("Cloudflare is blocking automated requests")
        if "maintenance" in location.lower() or (status in (502, 503) and "maintenance" in text[:5000].lower()):
            raise Maintenance("Codomo is down for maintenance")
        if status == 403:
            raise Blocked("Codomo refused the request (403)")
        if 300 <= status < 400:
            raise Changed(f"Codomo moved its pages (redirect to {location or 'somewhere else'})")
        if status in (404, 410):
            raise Changed("Codomo moved or removed the homes page")
        if status >= 500:
            raise Unavailable(f"Codomo is having trouble (HTTP {status})")
        if status != 200:
            raise Changed(f"Unexpected answer from Codomo (HTTP {status})")
        return text

    def homes(self, country: str, params: dict[str, str]) -> tuple[list[codomo.Card], codomo.Counts]:
        """One list page: the home cards and the page's own counts."""
        html = self.get(f"/homes/{country}/en", params or None)
        try:
            return codomo.parse_list(html)
        except codomo.PageError as e:
            raise Changed(f"Codomo changed its homes page ({e})") from None

    def unit(self, path: str) -> codomo.UnitPage:
        """A home's own page: maximum stay, exact costs, deposit."""
        html = self.get(path)
        try:
            return codomo.parse_unit(html)
        except codomo.PageError as e:
            raise Changed(f"Codomo changed its home pages ({e})") from None

    def cities(self) -> list[codomo.City]:
        html = self.get("/homes/nl/en")
        try:
            return codomo.parse_cities(html)
        except codomo.PageError as e:
            raise Changed(f"Codomo changed its city list ({e})") from None

    def sitemap(self) -> str:
        return self.get("/sitemap.xml")

    def photo(self, url: str) -> tuple[int, str]:
        """Status and type of a photo (they come from images.codomoliving.com)."""
        try:
            r = self.session.get(url, timeout=self.timeout, stream=True)
        except requests.RequestException as e:
            raise Unavailable(f"Can't load the photo ({type(e).__name__})") from None
        r.close()
        return r.status_code, r.headers.get("Content-Type", "")
