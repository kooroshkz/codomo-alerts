"""Names used by Codomo, with readable labels and the words people type."""

from __future__ import annotations

import re

# our status name -> the site's publish_mode
STATUS = {"available": "direct_booking", "interest": "interest"}

# countries with homes on codomo.eu on 2026-11-17; a new one is read when the site lists it
MARKETS = {"nl": "Netherlands", "es": "Spain", "pt": "Portugal", "at": "Austria"}
MARKET_ALIASES = {
    "holland": "nl", "the netherlands": "nl", "nederland": "nl", "niederlande": "nl", "paises bajos": "nl",
    "spain": "es", "espana": "es", "españa": "es", "spanje": "es", "spanien": "es", "espanha": "es",
    "austria": "at", "osterreich": "at", "österreich": "at", "oostenrijk": "at", "áustria": "at",
}

# Cities on codomo.eu on 2026-11-15, with their market. `codomo-alerts cities` shows new ones.
CITIES: dict[str, str] = {
    "Amersfoort": "nl", "Amsterdam": "nl", "Arnhem": "nl", "Capelle aan den IJssel": "nl",
    "Delft": "nl", "Den Bosch": "nl", "Diemen": "nl", "Dordrecht": "nl", "Eindhoven": "nl",
    "Groningen": "nl", "Haarlem": "nl", "Helmond": "nl", "Leiden": "nl", "Maarssen": "nl",
    "Maastricht": "nl", "Nieuwegein": "nl", "Nijmegen": "nl", "Rijswijk": "nl", "Rotterdam": "nl",
    "Sittard": "nl", "The Hague": "nl", "Tilburg": "nl", "Utrecht": "nl", "Velp": "nl", "Zeist": "nl",
    "Zoetermeer": "nl",
    "Linz": "at", "Granada": "es", "Carcavelos": "pt",
}
# the site's URL names where they differ from the city name
SLUGS = {"The Hague": "den-haag"}

CITY_ALIASES = {
    "den haag": "the hague",
    "hague": "the hague",
    "'s gravenhage": "the hague",
    "s gravenhage": "the hague",
    "'s hertogenbosch": "den bosch",
    "s hertogenbosch": "den bosch",
    "hertogenbosch": "den bosch",
    "capelle": "capelle aan den ijssel",
    "lisbon": "carcavelos",
    "lisboa": "carcavelos",
}

MAX_BEDROOMS = 9

CONTRACTS = {"indefinite": "Indefinite", "2y": "Max 2 years", "1y": "Max 1 year",
             "6m": "Max 6 months", "4m": "Max 4 months"}
CONTRACT_KEYS = {
    "indefinite": ["indefinite"],
    "2y": ["2y"],
    "1y": ["1y"],
    "6m": ["6m"],
    "4m": ["4m"],
    "long": ["indefinite", "2y", "1y"],
    "short": ["short"],          # every maximum under a year
}

FURNISHING = {"fully-furnished": "Fully furnished", "furnished": "Furnished",
              "semi-furnished": "Semi-furnished", "unfurnished": "Unfurnished"}
FURNISHING_ALIASES = {
    "fully": "fully-furnished", "semi": "semi-furnished", "none": "unfurnished",
    "volledig-gemeubileerd": "fully-furnished", "gemeubileerd": "furnished",
    "gestoffeerd": "semi-furnished", "ongemeubileerd": "unfurnished", "kaal": "unfurnished",
}

GENDERS = {"female": "Female only", "male": "Male only"}
GENDER_ALIASES = {"f": "female", "woman": "female", "women": "female", "m": "male", "man": "male", "men": "male"}

PERSONS = {"one": 1, "single": 1, "couple": 2, "two": 2, "three": 3, "four": 4, "family": 3}


def norm(text: str) -> str:
    return " ".join(str(text).strip().lower().replace("’", "'").replace("-", " ").split())


def city_name(name: str) -> str:
    """The city's name as Codomo lists it: 'den-haag' and 'Den Haag' -> 'The Hague'."""
    key = norm(name)
    key = CITY_ALIASES.get(key, key)
    for known in CITIES:
        if norm(known) == key:
            return known
    raise KeyError(name)


def same_city(a: str, b: str) -> bool:
    ka, kb = norm(a), norm(b)
    return CITY_ALIASES.get(ka, ka) == CITY_ALIASES.get(kb, kb)


def city_label(name: str | None) -> str:
    if not name:
        return ""
    try:
        return city_name(name)
    except KeyError:
        return name


def city_slug(name: str) -> str:
    return SLUGS.get(name, norm(name).replace(" ", "-"))


def market_of(name: str) -> str | None:
    return CITIES.get(city_label(name))


def market(value: str) -> list[str]:
    """'Spain', 'españa' and 'es' -> ['es']. 'all' -> [] (every country)."""
    key = norm(value)
    if key in ("all", "*", "any", "every", "everywhere"):
        return []
    if key in MARKETS:
        return [key]
    if key in MARKET_ALIASES:
        return [MARKET_ALIASES[key]]
    for code, name in MARKETS.items():
        if norm(name) == key:
            return [code]
    raise KeyError(value)


def market_label(code: str) -> str:
    return MARKETS.get(code, code.upper())


def gender(value: str) -> str:
    key = norm(value)
    key = GENDER_ALIASES.get(key, key)
    if key not in GENDERS:
        raise KeyError(value)
    return key


def gender_of(tags: list[str]) -> str | None:
    """The gender a home is for when Codomo marks it 'Female only' or 'Male only'."""
    for tag in tags:
        for key, label in GENDERS.items():
            if norm(tag) == norm(label):
                return key
    return None


def bedrooms(value: str) -> list[int]:
    """'studio' (and 'loft') is 0. '2', '2+' (two or more), '1-3'."""
    key = norm(value).replace("bedrooms", "").replace("bedroom", "").strip()
    key = {"studio": "0", "loft": "0"}.get(key, key)
    if re.fullmatch(r"\d+\+", key):
        return list(range(int(key[:-1]), MAX_BEDROOMS + 1))
    m = re.fullmatch(r"(\w+) ?- ?(\w+)", value.strip().lower())
    if m:
        a, b = ({"studio": "0", "loft": "0"}.get(g, g) for g in m.groups())
        if a.isdigit() and b.isdigit():
            lo, hi = sorted((int(a), int(b)))
            return list(range(lo, hi + 1))
    if key.isdigit() and int(key) <= MAX_BEDROOMS:
        return [int(key)]
    raise KeyError(value)


def bedrooms_label(n: int | None) -> str:
    if n is None:
        return ""
    if n == 0:
        return "Studio"
    return "1 bedroom" if n == 1 else f"{n} bedrooms"


def contracts(value: str) -> list[str]:
    key = norm(value).replace(" ", "").replace("_", "")
    key = {"shortstay": "short", "longstay": "long", "1year": "1y", "2years": "2y",
           "1ymax": "1y", "6mmax": "6m", "4mmax": "4m"}.get(key, key)
    if key not in CONTRACT_KEYS:
        raise KeyError(value)
    return CONTRACT_KEYS[key]


def contract_ok(key: str | None, wanted: list[str]) -> bool:
    if not wanted:
        return True
    if key is None:
        return False
    return key in wanted or ("short" in wanted and key.endswith("m"))


def contract_label(key: str | None) -> str:
    if not key:
        return ""
    if key in CONTRACTS:
        return CONTRACTS[key]
    m = re.fullmatch(r"(\d+)m", key)
    return f"Max {m[1]} months" if m else key


def furnishing(value: str) -> str:
    key = norm(value).replace(" ", "-")
    key = FURNISHING_ALIASES.get(key, key)
    if key not in FURNISHING:
        raise KeyError(value)
    return key


def furnishing_of(label: str | None) -> str | None:
    """The key for what a home card says ('Semi furnished' -> 'semi-furnished')."""
    if not label:
        return None
    try:
        return furnishing(label)
    except KeyError:
        return None


def persons(value) -> int:
    key = norm(str(value))
    if key.isdigit() and 1 <= int(key) <= 12:
        return int(key)
    if key in PERSONS:
        return PERSONS[key]
    raise KeyError(value)
