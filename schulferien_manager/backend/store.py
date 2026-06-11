"""Persistente Speicherung der konfigurierten Regionen (/data/regions.json)."""
from __future__ import annotations

import json
import os
import threading
import uuid

DATA_DIR = os.environ.get("DATA_DIR", "./data")
REGIONS_FILE = os.path.join(DATA_DIR, "regions.json")
_lock = threading.Lock()


def load_regions() -> list[dict]:
    with _lock:
        if not os.path.exists(REGIONS_FILE):
            return []
        try:
            with open(REGIONS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []


def _save(regions: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = REGIONS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(regions, f, ensure_ascii=False, indent=2)
    os.replace(tmp, REGIONS_FILE)


def add_region(
    country: str,
    subdivision: str,
    label: str,
    holidays_only: bool,
    language: str = "DE",
) -> dict:
    region = {
        "id": uuid.uuid4().hex[:8],
        "country": country.upper(),
        "subdivision": subdivision.upper() if subdivision else "",
        "label": label,
        "holidays_only": bool(holidays_only),
        "language": language.upper(),
    }
    with _lock:
        regions = []
        if os.path.exists(REGIONS_FILE):
            try:
                with open(REGIONS_FILE, encoding="utf-8") as f:
                    regions = json.load(f)
            except (json.JSONDecodeError, OSError):
                regions = []
        regions.append(region)
        _save(regions)
    return region


def delete_region(region_id: str) -> dict | None:
    with _lock:
        regions = []
        if os.path.exists(REGIONS_FILE):
            try:
                with open(REGIONS_FILE, encoding="utf-8") as f:
                    regions = json.load(f)
            except (json.JSONDecodeError, OSError):
                regions = []
        removed = next((r for r in regions if r["id"] == region_id), None)
        if removed:
            regions = [r for r in regions if r["id"] != region_id]
            _save(regions)
        return removed
