"""Client für die OpenHolidays API (openholidaysapi.org) mit einfachem Cache."""
from __future__ import annotations

import logging
import threading
import time

import requests

_LOGGER = logging.getLogger(__name__)

API_BASE = "https://openholidaysapi.org"
TIMEOUT = 30

_cache: dict = {}
_cache_lock = threading.Lock()


def _get(path: str, params: dict, ttl: int) -> list:
    key = (path, tuple(sorted(params.items())))
    now = time.time()
    with _cache_lock:
        if key in _cache and now - _cache[key][0] < ttl:
            return _cache[key][1]
    resp = requests.get(
        f"{API_BASE}{path}",
        params=params,
        headers={"Accept": "application/json"},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    with _cache_lock:
        _cache[key] = (now, data)
    return data


def localized_name(name_list: list | None, language: str) -> str:
    """Lokalisierten Namen aus einer OpenHolidays-Namensliste extrahieren."""
    names = name_list or []
    for entry in names:
        if entry.get("language", "").upper() == language.upper():
            return entry.get("text", "Unbekannt")
    if names:
        return names[0].get("text", "Unbekannt")
    return "Unbekannt"


def get_countries(language: str = "DE") -> list:
    return _get("/Countries", {"languageIsoCode": language}, ttl=86400)


def get_subdivisions(country: str, language: str = "DE") -> list:
    return _get(
        "/Subdivisions",
        {"countryIsoCode": country, "languageIsoCode": language},
        ttl=86400,
    )


def fetch_school_holidays(
    country: str, subdivision: str, language: str, valid_from: str, valid_to: str
) -> list:
    params = {
        "countryIsoCode": country,
        "languageIsoCode": language,
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    if subdivision:
        params["subdivisionCode"] = subdivision
    return _get("/SchoolHolidays", params, ttl=3600)


def fetch_public_holidays(
    country: str, subdivision: str, language: str, valid_from: str, valid_to: str
) -> list:
    params = {
        "countryIsoCode": country,
        "languageIsoCode": language,
        "validFrom": valid_from,
        "validTo": valid_to,
    }
    if subdivision:
        params["subdivisionCode"] = subdivision
    return _get("/PublicHolidays", params, ttl=3600)
