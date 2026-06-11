"""API-Provider: mehrere keylose Datenquellen mit Verfügbarkeitstest und Fallback.

Alle fetch_periods()-Aufrufe liefern normalisierte Zeiträume: {name, start, end}.
"""
from __future__ import annotations

import logging
import time
from datetime import date

import requests

import holidays_api

_LOGGER = logging.getLogger(__name__)
TIMEOUT = 30

PROVIDERS: dict[str, dict] = {
    "openholidays": {
        "name": "OpenHolidays API",
        "school": True,
        "public": True,
        "countries": None,  # alle
        "test_url": "https://openholidaysapi.org/Countries?languageIsoCode=DE",
        "hint": "Schulferien + Feiertage, international (Standard)",
    },
    "german_apis": {
        "name": "ferien-api.de + feiertage-api.de",
        "school": True,
        "public": True,
        "countries": ["DE"],
        "test_url": "https://ferien-api.de/api/v1/holidays/BY",
        "hint": "Schulferien + Feiertage, nur Deutschland",
    },
    "nager": {
        "name": "Nager.Date",
        "school": False,
        "public": True,
        "countries": None,
        "test_url": "https://date.nager.at/api/v3/AvailableCountries",
        "hint": "Nur Feiertage, international",
    },
}


def provider_catalog() -> list[dict]:
    return [
        {"id": pid, "name": p["name"], "school": p["school"], "public": p["public"],
         "countries": p["countries"], "hint": p["hint"]}
        for pid, p in PROVIDERS.items()
    ]


def test_provider(pid: str) -> dict:
    """Live-Verfügbarkeitstest eines Providers."""
    prov = PROVIDERS.get(pid)
    if prov is None:
        return {"ok": False, "message": f"Unbekannter Provider: {pid}"}
    start = time.time()
    try:
        resp = requests.get(prov["test_url"], timeout=10, headers={"Accept": "application/json"})
        ms = int((time.time() - start) * 1000)
        if resp.status_code == 200 and resp.json():
            return {"ok": True, "message": f"{prov['name']} erreichbar ({ms} ms)", "ms": ms}
        return {"ok": False, "message": f"{prov['name']}: HTTP {resp.status_code}"}
    except Exception as err:  # noqa: BLE001
        return {"ok": False, "message": f"{prov['name']} nicht erreichbar: {err}"}


def supports(pid: str, kind: str, country: str) -> bool:
    prov = PROVIDERS.get(pid)
    if prov is None or not prov.get(kind, False):
        return False
    return prov["countries"] is None or country.upper() in prov["countries"]


def fetch_periods(
    pid: str, kind: str, country: str, subdivision: str, language: str,
    valid_from: date, valid_to: date,
) -> list[dict]:
    """kind: 'school' oder 'public'. Wirft Exception bei API-Fehlern."""
    if pid == "openholidays":
        return _openholidays(kind, country, subdivision, language, valid_from, valid_to)
    if pid == "german_apis":
        if kind == "school":
            return _ferienapi_school(country, subdivision, valid_from, valid_to)
        return _feiertageapi_public(country, subdivision, valid_from, valid_to)
    if pid == "nager":
        if kind == "school":
            raise ValueError("Nager.Date unterstützt keine Schulferien")
        return _nager_public(country, subdivision, valid_from, valid_to)
    raise ValueError(f"Unbekannter Provider: {pid}")


# ---------------------------------------------------------------- OpenHolidays

def _subdivision_applies(item: dict, country: str, requested: str) -> bool:
    """Eintrag gilt nur, wenn er die GESAMTE angefragte Region abdeckt.

    Beispiel Friedensfest: subdivisions=[DE-BY-A]. Bei Abfrage DE-BY (ganz
    Bayern) wird er ausgeschlossen, bei Abfrage DE-BY-A eingeschlossen.
    """
    if item.get("nationwide"):
        return True
    subs = item.get("subdivisions") or []
    if not subs or not requested:
        return True
    requested = requested.upper()
    for s in subs:
        code = (s.get("code") or "").upper()
        if not code:
            short = (s.get("shortName") or "").upper()
            code = f"{country.upper()}-{short}" if short else ""
        if not code:
            continue
        # Code deckt die Anfrage ab, wenn er gleich oder ein Vorfahre ist
        if requested == code or requested.startswith(code + "-"):
            return True
    return False


def _openholidays(kind, country, subdivision, language, valid_from, valid_to):
    fetch = (
        holidays_api.fetch_school_holidays
        if kind == "school"
        else holidays_api.fetch_public_holidays
    )
    raw = fetch(country, subdivision, language, valid_from.isoformat(), valid_to.isoformat())
    raw = [item for item in raw if _subdivision_applies(item, country, subdivision)]
    return _parse_openholidays(raw, language)


def _parse_openholidays(raw: list, language: str) -> list[dict]:
    periods = []
    for item in raw:
        try:
            periods.append(
                {
                    "name": holidays_api.localized_name(item.get("name"), language),
                    "start": date.fromisoformat(item["startDate"]),
                    "end": date.fromisoformat(item["endDate"]),
                }
            )
        except (KeyError, ValueError, TypeError):
            continue
    periods.sort(key=lambda p: p["start"])
    return periods


# ---------------------------------------------------------------- ferien-api.de

def _state_code(subdivision: str) -> str:
    # "DE-BY" oder "DE-BY-A" -> "BY"
    parts = (subdivision or "").split("-")
    if len(parts) < 2 or not parts[1]:
        raise ValueError("Für diese API wird ein Bundesland benötigt (z. B. DE-BY)")
    return parts[1].upper()


def _ferienapi_school(country, subdivision, valid_from, valid_to):
    if country.upper() != "DE":
        raise ValueError("ferien-api.de unterstützt nur Deutschland")
    state = _state_code(subdivision)
    resp = requests.get(
        f"https://ferien-api.de/api/v1/holidays/{state}",
        timeout=TIMEOUT, headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    periods = []
    for item in resp.json():
        try:
            start = date.fromisoformat(item["start"][:10])
            end = date.fromisoformat(item["end"][:10])
        except (KeyError, ValueError):
            continue
        if end < valid_from or start > valid_to:
            continue
        name = (item.get("name") or "Ferien").split(" ")[0].capitalize()
        periods.append({"name": name, "start": start, "end": end})
    periods.sort(key=lambda p: p["start"])
    return periods


# ---------------------------------------------------------------- feiertage-api.de

def _feiertageapi_public(country, subdivision, valid_from, valid_to):
    if country.upper() != "DE":
        raise ValueError("feiertage-api.de unterstützt nur Deutschland")
    state = _state_code(subdivision) if subdivision else "NATIONAL"
    periods = []
    for year in range(valid_from.year, valid_to.year + 1):
        resp = requests.get(
            "https://feiertage-api.de/api/",
            params={"jahr": year, "nur_land": state},
            timeout=TIMEOUT, headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        for name, info in resp.json().items():
            hinweis = (info.get("hinweis") or "").lower()
            # Regional begrenzte Feiertage ("nur in ...") überspringen
            if "nur" in hinweis:
                continue
            try:
                d = date.fromisoformat(info["datum"])
            except (KeyError, ValueError):
                continue
            if valid_from <= d <= valid_to:
                periods.append({"name": name.title() if name.isupper() else name,
                                "start": d, "end": d})
    periods.sort(key=lambda p: p["start"])
    return periods


# ---------------------------------------------------------------- Nager.Date

def _nager_public(country, subdivision, valid_from, valid_to):
    c2 = country.upper()[:2]
    requested = (subdivision or "").upper()
    periods = []
    for year in range(valid_from.year, valid_to.year + 1):
        resp = requests.get(
            f"https://date.nager.at/api/v3/PublicHolidays/{year}/{c2}",
            timeout=TIMEOUT, headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        for item in resp.json():
            counties = item.get("counties")
            if counties and requested and not any(
                requested == c.upper() or requested.startswith(c.upper() + "-")
                for c in counties
            ):
                continue
            try:
                d = date.fromisoformat(item["date"])
            except (KeyError, ValueError):
                continue
            if valid_from <= d <= valid_to:
                periods.append(
                    {"name": item.get("localName") or item.get("name", "Feiertag"),
                     "start": d, "end": d}
                )
    periods.sort(key=lambda p: p["start"])
    return periods
