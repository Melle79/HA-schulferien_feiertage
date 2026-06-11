"""Kernlogik: Ferien-/Feiertagszeiträume auswerten, Entitätszustände berechnen."""
from __future__ import annotations

from datetime import date, timedelta

import holidays_api


def parse_periods(raw: list, language: str) -> list[dict]:
    """API-Rohdaten in sortierte Zeiträume {name, start, end} umwandeln."""
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


def period_on(periods: list[dict], day: date) -> dict | None:
    for p in periods:
        if p["start"] <= day <= p["end"]:
            return p
    return None


def next_period(periods: list[dict], after: date) -> dict | None:
    for p in periods:
        if p["start"] > after:
            return p
    return None


def is_school_free(
    school: list[dict], public: list[dict], day: date, weekend_free: bool = True
) -> tuple[bool, str | None]:
    if (holiday := period_on(public, day)) is not None:
        return True, f"Feiertag: {holiday['name']}"
    if (ferien := period_on(school, day)) is not None:
        return True, f"Ferien: {ferien['name']}"
    if weekend_free and day.weekday() >= 5:
        return True, "Wochenende"
    return False, None


def build_states(region: dict, data: dict, today: date | None = None) -> dict:
    """Alle Entitätszustände (state + Attribute) für eine Region berechnen."""
    today = today or date.today()
    tomorrow = today + timedelta(days=1)
    school = data.get("school", [])
    public = data.get("public", [])
    holidays_only = region.get("holidays_only", False)

    states: dict[str, dict] = {}

    for key, day in (("heute_feiertag", today), ("morgen_feiertag", tomorrow)):
        holiday = period_on(public, day)
        states[key] = {
            "state": "ON" if holiday else "OFF",
            "attributes": {
                "datum": day.isoformat(),
                "name": holiday["name"] if holiday else None,
            },
        }

    next_pub = next_period(public, today)
    states["naechster_feiertag"] = {
        "state": next_pub["name"] if next_pub else "unknown",
        "attributes": {
            "datum": next_pub["start"].isoformat() if next_pub else None,
            "in_tagen": (next_pub["start"] - today).days if next_pub else None,
            "vorschau": build_day_strip(data, holidays_only, today=today),
        },
    }

    if not holidays_only:
        for key, day in (("heute_schulfrei", today), ("morgen_schulfrei", tomorrow)):
            free, grund = is_school_free(school, public, day)
            states[key] = {
                "state": "ON" if free else "OFF",
                "attributes": {"datum": day.isoformat(), "grund": grund},
            }

        next_school = next_period(school, today)
        current = period_on(school, today)
        states["naechste_schulferien"] = {
            "state": next_school["name"] if next_school else "unknown",
            "attributes": {
                "beginn": next_school["start"].isoformat() if next_school else None,
                "ende": next_school["end"].isoformat() if next_school else None,
                "in_tagen": (next_school["start"] - today).days if next_school else None,
                "dauer_tage": (next_school["end"] - next_school["start"]).days + 1
                if next_school
                else None,
                "aktuell_ferien": current["name"] if current else None,
            },
        }

    return states


def build_preview(data: dict, holidays_only: bool, limit: int = 6, today: date | None = None) -> list[dict]:
    """Chronologische Vorschau der nächsten Ferien/Feiertage (inkl. laufender)."""
    today = today or date.today()
    events: list[dict] = []

    for p in data.get("public", []):
        if p["end"] >= today:
            events.append({"type": "feiertag", **_event(p, today)})
    if not holidays_only:
        for p in data.get("school", []):
            if p["end"] >= today:
                events.append({"type": "ferien", **_event(p, today)})

    events.sort(key=lambda e: e["start"])
    return events[:limit]


def build_combined_state(region: dict, data: dict, today: date | None = None) -> dict:
    """Eine einzelne Entität mit allen Daten als Attribute."""
    today = today or date.today()
    tomorrow = today + timedelta(days=1)
    school = data.get("school", [])
    public = data.get("public", [])
    holidays_only = region.get("holidays_only", False)

    heute_ft = period_on(public, today)
    morgen_ft = period_on(public, tomorrow)
    next_pub = next_period(public, today)

    attrs: dict = {
        "datum": today.isoformat(),
        "heute_feiertag": heute_ft is not None,
        "heute_feiertag_name": heute_ft["name"] if heute_ft else None,
        "morgen_feiertag": morgen_ft is not None,
        "morgen_feiertag_name": morgen_ft["name"] if morgen_ft else None,
        "naechster_feiertag": next_pub["name"] if next_pub else None,
        "naechster_feiertag_datum": next_pub["start"].isoformat() if next_pub else None,
        "naechster_feiertag_in_tagen": (next_pub["start"] - today).days if next_pub else None,
        "vorschau": build_day_strip(data, holidays_only, today=today),
    }

    if holidays_only:
        state = "Feiertag" if heute_ft else "Kein Feiertag"
        return {"state": state, "attributes": attrs}

    heute_frei, heute_grund = is_school_free(school, public, today)
    morgen_frei, morgen_grund = is_school_free(school, public, tomorrow)
    next_school = next_period(school, today)
    current = period_on(school, today)

    attrs.update(
        {
            "heute_schulfrei": heute_frei,
            "heute_grund": heute_grund,
            "morgen_schulfrei": morgen_frei,
            "morgen_grund": morgen_grund,
            "naechste_schulferien": next_school["name"] if next_school else None,
            "schulferien_beginn": next_school["start"].isoformat() if next_school else None,
            "schulferien_ende": next_school["end"].isoformat() if next_school else None,
            "schulferien_in_tagen": (next_school["start"] - today).days if next_school else None,
            "schulferien_dauer_tage": (next_school["end"] - next_school["start"]).days + 1
            if next_school
            else None,
            "aktuell_ferien": current["name"] if current else None,
        }
    )

    if heute_ft:
        state = "Feiertag"
    elif current:
        state = "Ferien"
    elif today.weekday() >= 5:
        state = "Wochenende"
    else:
        state = "Schule"
    return {"state": state, "attributes": attrs}


def build_day_strip(
    data: dict, holidays_only: bool, days: int = 14, today: date | None = None
) -> list[dict]:
    """Status der nächsten N Tage für den Vorschau-Streifen in der UI."""
    today = today or date.today()
    school = data.get("school", [])
    public = data.get("public", [])
    strip = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        if period_on(public, day):
            status = "feiertag"
        elif not holidays_only and period_on(school, day):
            status = "ferien"
        elif not holidays_only and day.weekday() >= 5:
            status = "wochenende"
        else:
            status = "normal"
        strip.append(
            {
                "date": day.isoformat(),
                "day": day.day,
                "weekday": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][day.weekday()],
                "status": status,
            }
        )
    return strip


def _event(p: dict, today: date) -> dict:
    return {
        "name": p["name"],
        "start": p["start"].isoformat(),
        "end": p["end"].isoformat(),
        "in_tagen": (p["start"] - today).days,
        "laufend": p["start"] <= today <= p["end"],
        "dauer_tage": (p["end"] - p["start"]).days + 1,
    }
