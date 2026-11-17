"""Settings from config.toml and CODOMO_* environment variables (env wins)."""

from __future__ import annotations

import json
import os
import re
import sys
import tomllib
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import date, time
from pathlib import Path

from . import catalog

MIN_INTERVAL = 60
PRESETS = {
    # seconds between checks: release hours, rest of the day, night
    "relaxed": (300, 600, 1800),
    "normal": (120, 300, 900),
    "eager": (60, 180, 600),
}
DEFAULT_BASE_URL = "https://codomo.eu"
NAME = "codomo-alerts"


class ConfigError(Exception):
    pass


@dataclass
class Search:
    countries: list[str] = field(default_factory=list)    # empty: every country
    cities: list[str] = field(default_factory=list)
    exclude_cities: list[str] = field(default_factory=list)
    bedrooms: list[int] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    persons: int | None = None
    furnishing: list[str] = field(default_factory=list)
    price_min: int | None = None
    price_max: int | None = None
    move_in_before: date | None = None
    gender: str | None = None     # skip homes Codomo keeps for the other gender
    interest: bool = True

    def fingerprint(self) -> str:
        data = asdict(self)
        data.pop("interest")
        data["move_in_before"] = str(self.move_in_before or "")
        return json.dumps(data, sort_keys=True)

    def markets(self, seen: Iterable[str] = ()) -> list[str]:
        """Countries to read: those of the named cities, else the named countries, else every
        country Codomo lists (`seen` adds countries found on the site since this release)."""
        if self.cities:
            return list(dict.fromkeys(catalog.market_of(c) or "nl" for c in self.cities))
        if self.countries:
            return list(self.countries)
        return list(dict.fromkeys([*catalog.MARKETS, *seen]))

    def summary(self) -> str:
        if self.cities:
            where = ", ".join(self.cities)
        elif self.countries:
            where = "All cities in " + ", ".join("the Netherlands" if c == "nl" else catalog.market_label(c)
                                                 for c in self.countries)
        else:
            where = "Every Codomo city"
        parts = [where]
        if self.exclude_cities:
            parts.append("not " + ", ".join(self.exclude_cities))
        if self.bedrooms:
            b = self.bedrooms
            if len(b) > 1 and b == list(range(b[0], catalog.MAX_BEDROOMS + 1)):
                parts.append("studio or bigger" if b[0] == 0 else f"{b[0]}+ bedrooms")
            else:
                parts.append(", ".join(catalog.bedrooms_label(n) for n in b))
        if self.price_min and self.price_max:
            parts.append(f"€{self.price_min:,} to €{self.price_max:,}")
        elif self.price_max:
            parts.append(f"up to €{self.price_max:,}")
        elif self.price_min:
            parts.append(f"from €{self.price_min:,}")
        if self.contracts:
            if sorted(self.contracts) == sorted(catalog.CONTRACT_KEYS["long"]):
                parts.append("Long stay")
            elif self.contracts == ["short"]:
                parts.append("Short stay")
            else:
                parts.append(", ".join("Short stay" if c == "short" else catalog.contract_label(c)
                                       for c in self.contracts))
        if self.furnishing:
            parts.append(", ".join(catalog.FURNISHING[f] for f in self.furnishing))
        if self.persons:
            parts.append(f"for {self.persons} people" if self.persons > 1 else "for 1 person")
        if self.move_in_before:
            parts.append(f"move in by {self.move_in_before:%d %b}")
        if self.gender:
            parts.append("open to women" if self.gender == "female" else "open to men")
        return " · ".join(parts)


@dataclass
class Notify:
    urls: list[str] = field(default_factory=list)
    quiet_hours: tuple[time, time] | None = None
    existing_on_start: bool = False
    health: bool = True
    digest_after: int = 4


@dataclass
class Schedule:
    preset: str = "normal"
    hot: int = PRESETS["normal"][0]
    day: int = PRESETS["normal"][1]
    night: int = PRESETS["normal"][2]
    interest: int = 600
    jitter: float = 0.25


@dataclass
class Dashboard:
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8080
    password: str | None = None


@dataclass
class Config:
    search: Search = field(default_factory=Search)
    notify: Notify = field(default_factory=Notify)
    schedule: Schedule = field(default_factory=Schedule)
    dashboard: Dashboard = field(default_factory=Dashboard)
    base_url: str = DEFAULT_BASE_URL
    data_dir: Path = field(default_factory=lambda: default_data_dir())
    log_level: str = "INFO"
    source: Path | None = None
    warnings: list[str] = field(default_factory=list)


def default_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / NAME


def config_candidates() -> list[Path]:
    xdg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return [Path("config.toml"), xdg / NAME / "config.toml"]


def find_config(path: str | None, env: dict) -> Path | None:
    if path:
        p = Path(path).expanduser()
        if not p.exists():
            raise ConfigError(f"Config file not found: {p}")
        return p
    if env.get("CODOMO_CONFIG"):
        p = Path(env["CODOMO_CONFIG"]).expanduser()
        if not p.exists():
            raise ConfigError(f"CODOMO_CONFIG points to a missing file: {p}")
        return p
    return next((p for p in config_candidates() if p.exists()), None)


# Parsing helpers

def _list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, int | float):
        return [str(value)]
    return [str(v).strip() for v in value if str(v).strip()]


def _bool(value, name: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off", ""):
        return False
    raise ConfigError(f"{name}: expected true or false, got {value!r}")


def _int(value, name: str, lo: int | None = None) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(str(value).replace("€", "").replace(",", "").replace("_", "").strip())
    except ValueError:
        raise ConfigError(f"{name}: expected a whole number, got {value!r}") from None
    if lo is not None and n < lo:
        raise ConfigError(f"{name}: must be at least {lo}")
    return n


def _resolve(values: list[str], fn, name: str, options: str) -> list:
    out: list = []
    for v in values:
        try:
            r = fn(v)
        except KeyError:
            raise ConfigError(f"{name}: unknown value {v!r}. Use {options}") from None
        out.extend(r if isinstance(r, list) else [r])
    return list(dict.fromkeys(out))


def _cities(values: list[str], name: str) -> list[str]:
    known = ", ".join(catalog.CITIES)
    return _resolve(values, catalog.city_name, name,
                    f"a city name ({known}). `codomo-alerts cities` shows what is listed now")


def _clock(text: str, name: str) -> time:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", text.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        raise ConfigError(f"{name}: expected HH:MM, got {text!r}")
    return time(int(m[1]), int(m[2]))


def _quiet(value, name: str) -> tuple[time, time] | None:
    if not value:
        return None
    parts = str(value).split("-")
    if len(parts) != 2:
        raise ConfigError(f"{name}: expected a range like 23:00-07:00")
    return _clock(parts[0], name), _clock(parts[1], name)


def _urls(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [u for u in re.split(r"[\s;]+", value) if u]
    return [str(u).strip() for u in value if str(u).strip()]


# Loading

def load(path: str | None = None, env: dict | None = None) -> Config:
    env = dict(os.environ if env is None else env)
    source = find_config(path, env)
    raw: dict = {}
    if source:
        try:
            raw = tomllib.loads(source.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{source}: {e}") from None
    return build(raw, env, source)


def build(raw: dict, env: dict, source: Path | None = None) -> Config:
    s, n, sc, d, g = (raw.get(k, {}) for k in ("search", "notify", "schedule", "dashboard", "general"))
    for section, value in (("search", s), ("notify", n), ("schedule", sc), ("dashboard", d), ("general", g)):
        if not isinstance(value, dict):
            raise ConfigError(f"[{section}] must be a table")

    def pick(env_key: str, table: dict, key: str, default=None):
        return env[env_key] if env.get(env_key, "") != "" else table.get(key, default)

    cfg = Config(source=source)

    search = Search()
    search.countries = _resolve(_list(pick("CODOMO_COUNTRIES", s, "countries")), catalog.market, "countries",
                                ", ".join(catalog.MARKETS.values()) + " or all")
    search.cities = _cities(_list(pick("CODOMO_CITIES", s, "cities")), "cities")
    search.exclude_cities = _cities(_list(pick("CODOMO_EXCLUDE_CITIES", s, "exclude_cities")), "exclude_cities")
    search.bedrooms = sorted(_resolve(_list(pick("CODOMO_BEDROOMS", s, "bedrooms")), catalog.bedrooms,
                                      "bedrooms", "studio, loft, 1, 2, 3, 4, 2+ or 1-3"))
    search.contracts = _resolve(_list(pick("CODOMO_CONTRACT", s, "contract")), catalog.contracts,
                                "contract", "long, short, indefinite, 2y, 1y, 6m or 4m")
    if "occupants" in s or env.get("CODOMO_OCCUPANTS"):
        raise ConfigError("occupants is gone: use persons, the number of people the home must fit (like 2)")
    persons = pick("CODOMO_PERSONS", s, "persons")
    if persons not in (None, ""):
        try:
            search.persons = catalog.persons(persons)
        except KeyError:
            raise ConfigError(f"persons: expected a number of people like 2, got {persons!r}") from None
    search.furnishing = _resolve(_list(pick("CODOMO_FURNISHING", s, "furnishing")), catalog.furnishing,
                                 "furnishing", "fully-furnished, furnished, semi-furnished or unfurnished")
    search.price_min = _int(pick("CODOMO_PRICE_MIN", s, "price_min"), "price_min", 0) or None
    search.price_max = _int(pick("CODOMO_PRICE_MAX", s, "price_max"), "price_max", 1) or None
    if search.price_min and search.price_max and search.price_min > search.price_max:
        raise ConfigError("price_min is higher than price_max")
    move = pick("CODOMO_MOVE_IN_BEFORE", s, "move_in_before")
    if move not in (None, ""):
        try:
            search.move_in_before = move if isinstance(move, date) else date.fromisoformat(str(move))
        except ValueError:
            raise ConfigError(f"move_in_before: expected YYYY-MM-DD, got {move!r}") from None
    gender = pick("CODOMO_GENDER", s, "gender")
    if gender not in (None, ""):
        try:
            search.gender = catalog.gender(str(gender))
        except KeyError:
            raise ConfigError(f"gender: expected female or male, got {gender!r}") from None
    interest = pick("CODOMO_INTEREST", s, "interest")
    if interest is None and "lottery" in s:
        interest = s["lottery"]
        cfg.warnings.append("lottery is now called interest: Codomo replaced the lottery with a shortlist")
    search.interest = _bool(True if interest is None else interest, "interest")
    overlap = {catalog.norm(c) for c in search.cities} & {catalog.norm(c) for c in search.exclude_cities}
    if overlap:
        names = ", ".join(c for c in search.cities if catalog.norm(c) in overlap)
        raise ConfigError(f"{names} is both in cities and exclude_cities")
    for city in search.cities:
        code = catalog.market_of(city)
        if search.countries and code not in search.countries:
            raise ConfigError(f"{city} is in {catalog.market_label(code or '')}, which is not in countries")
    cfg.search = search

    notify = Notify()
    urls = pick("CODOMO_NOTIFY", n, "urls")
    if env.get("CODOMO_NOTIFY_FILE"):
        try:
            urls = Path(env["CODOMO_NOTIFY_FILE"]).read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigError(f"CODOMO_NOTIFY_FILE: {e}") from None
    notify.urls = _urls(urls)
    notify.quiet_hours = _quiet(pick("CODOMO_QUIET_HOURS", n, "quiet_hours"), "quiet_hours")
    notify.existing_on_start = _bool(pick("CODOMO_NOTIFY_EXISTING", n, "existing_on_start", False),
                                     "existing_on_start")
    notify.health = _bool(pick("CODOMO_NOTIFY_HEALTH", n, "health", True), "health")
    notify.digest_after = _int(pick("CODOMO_DIGEST_AFTER", n, "digest_after", 4), "digest_after", 1)
    cfg.notify = notify

    sched = Schedule()
    preset = str(pick("CODOMO_SCHEDULE", sc, "preset", "normal")).strip().lower()
    if preset not in PRESETS:
        raise ConfigError(f"schedule preset: use {', '.join(PRESETS)}")
    sched.preset = preset
    sched.hot, sched.day, sched.night = PRESETS[preset]
    for key in ("hot", "day", "night", "interest"):
        value = _int(pick(f"CODOMO_{key.upper()}_SECONDS", sc, f"{key}_seconds"), f"{key}_seconds", 1)
        if value is None:
            continue
        if value < MIN_INTERVAL:
            cfg.warnings.append(f"{key}_seconds raised to {MIN_INTERVAL}: checking faster gets you blocked")
            value = MIN_INTERVAL
        setattr(sched, key, value)
    cfg.schedule = sched

    dash = Dashboard()
    dash.enabled = _bool(pick("CODOMO_DASHBOARD", d, "enabled", True), "dashboard")
    dash.host = str(pick("CODOMO_HOST", d, "host", "127.0.0.1"))
    dash.port = _int(pick("CODOMO_PORT", d, "port", 8080), "port", 1)
    if dash.port > 65535:
        raise ConfigError("port: must be 65535 or lower")
    password = pick("CODOMO_DASHBOARD_PASSWORD", d, "password")
    dash.password = str(password) if password not in (None, "") else None
    cfg.dashboard = dash

    base = str(pick("CODOMO_BASE_URL", g, "base_url", DEFAULT_BASE_URL)).rstrip("/")
    if not base.startswith("https://"):
        raise ConfigError("base_url must start with https://")
    cfg.base_url = base
    data_dir = pick("CODOMO_DATA_DIR", g, "data_dir")
    cfg.data_dir = Path(data_dir).expanduser() if data_dir else default_data_dir()
    cfg.log_level = str(pick("CODOMO_LOG_LEVEL", g, "log_level", "INFO")).upper()
    return cfg
