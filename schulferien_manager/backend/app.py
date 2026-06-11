"""Schulferien & Feiertage Manager – Flask-Backend des Home Assistant Add-ons."""
from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date, timedelta

from flask import Flask, jsonify, request, send_from_directory

import holidays_api
import logic
import store
from mqtt_publisher import Publisher

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
_LOGGER = logging.getLogger("schulferien")

FETCH_PAST_DAYS = 14
FETCH_FUTURE_DAYS = 540
REFRESH_INTERVAL = 12 * 3600

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# rid -> {"school": [...], "public": [...], "fetched": ts, "error": str|None}
region_data: dict[str, dict] = {}
_data_lock = threading.Lock()

publisher: Publisher | None = None


# ---------------------------------------------------------------- Daten laden

def refresh_region(region: dict) -> dict:
    """API-Daten für eine Region laden, Zustände berechnen und publizieren."""
    rid = region["id"]
    today = date.today()
    valid_from = (today - timedelta(days=FETCH_PAST_DAYS)).isoformat()
    valid_to = (today + timedelta(days=FETCH_FUTURE_DAYS)).isoformat()
    lang = region.get("language", "DE")

    entry = {"school": [], "public": [], "fetched": time.time(), "error": None}
    try:
        public_raw = holidays_api.fetch_public_holidays(
            region["country"], region.get("subdivision", ""), lang, valid_from, valid_to
        )
        entry["public"] = logic.parse_periods(public_raw, lang)

        if not region.get("holidays_only", False):
            school_raw = holidays_api.fetch_school_holidays(
                region["country"], region.get("subdivision", ""), lang, valid_from, valid_to
            )
            entry["school"] = logic.parse_periods(school_raw, lang)
        _LOGGER.info(
            "Region %s: %d Feiertage, %d Ferienzeiträume geladen",
            region["label"], len(entry["public"]), len(entry["school"]),
        )
    except Exception as err:  # noqa: BLE001
        entry["error"] = str(err)
        _LOGGER.error("Region %s: API-Fehler: %s", region["label"], err)

    with _data_lock:
        region_data[rid] = entry

    if publisher and entry["error"] is None:
        publisher.publish_discovery(region)
        publisher.publish_states(region, logic.build_states(region, entry))
    return entry


def refresh_all() -> None:
    for region in store.load_regions():
        refresh_region(region)


def _scheduler() -> None:
    """Alle 12 h neu laden; bei Datumswechsel Zustände neu publizieren."""
    last_day = date.today()
    while True:
        time.sleep(60)
        try:
            now = time.time()
            regions = store.load_regions()

            if date.today() != last_day:
                last_day = date.today()
                _LOGGER.info("Datumswechsel – Zustände werden neu berechnet")
                for region in regions:
                    with _data_lock:
                        entry = region_data.get(region["id"])
                    if publisher and entry and entry.get("error") is None:
                        publisher.publish_states(region, logic.build_states(region, entry))

            for region in regions:
                with _data_lock:
                    entry = region_data.get(region["id"])
                if entry is None or now - entry["fetched"] > REFRESH_INTERVAL:
                    refresh_region(region)
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Scheduler-Fehler: %s", err)


# ---------------------------------------------------------------- Hilfen

def _simplify_subdivision(item: dict, lang: str) -> dict:
    return {
        "code": item.get("code") or item.get("isoCode", ""),
        "name": holidays_api.localized_name(item.get("name"), lang),
        "shortName": item.get("shortName", ""),
        "children": [
            _simplify_subdivision(child, lang) for child in (item.get("children") or [])
        ],
    }


def _region_summary(region: dict) -> dict:
    with _data_lock:
        entry = region_data.get(region["id"])
    summary = dict(region)
    if entry is None:
        summary.update({"loaded": False, "error": None, "states": {}, "preview": []})
        return summary
    summary.update(
        {
            "loaded": entry["error"] is None,
            "error": entry["error"],
            "states": logic.build_states(region, entry) if entry["error"] is None else {},
            "preview": logic.build_preview(
                entry, region.get("holidays_only", False)
            )
            if entry["error"] is None
            else [],
            "day_strip": logic.build_day_strip(
                entry, region.get("holidays_only", False)
            )
            if entry["error"] is None
            else [],
        }
    )
    return summary


# ---------------------------------------------------------------- Routen

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def api_status():
    return jsonify(
        {
            "mqtt_connected": bool(publisher and publisher.connected.is_set()),
            "mqtt_configured": publisher is not None,
            "regions": len(store.load_regions()),
        }
    )


@app.get("/api/countries")
def api_countries():
    lang = request.args.get("lang", "DE")
    try:
        countries = [
            {
                "code": c.get("isoCode", ""),
                "name": holidays_api.localized_name(c.get("name"), lang),
            }
            for c in holidays_api.get_countries(lang)
        ]
        countries.sort(key=lambda c: c["name"])
        return jsonify(countries)
    except Exception as err:  # noqa: BLE001
        return jsonify({"error": str(err)}), 502


@app.get("/api/subdivisions/<country>")
def api_subdivisions(country: str):
    lang = request.args.get("lang", "DE")
    try:
        subs = [
            _simplify_subdivision(s, lang)
            for s in holidays_api.get_subdivisions(country.upper(), lang)
        ]
        return jsonify(subs)
    except Exception as err:  # noqa: BLE001
        return jsonify({"error": str(err)}), 502


@app.get("/api/regions")
def api_regions():
    return jsonify([_region_summary(r) for r in store.load_regions()])


@app.post("/api/regions")
def api_add_region():
    body = request.get_json(force=True, silent=True) or {}
    country = (body.get("country") or "").strip().upper()
    subdivision = (body.get("subdivision") or "").strip().upper()
    label = (body.get("label") or "").strip()
    holidays_only = bool(body.get("holidays_only", False))

    if not country:
        return jsonify({"error": "Land fehlt"}), 400
    if not label:
        label = subdivision or country

    for existing in store.load_regions():
        if (
            existing["country"] == country
            and existing.get("subdivision", "") == subdivision
            and existing.get("holidays_only", False) == holidays_only
        ):
            return jsonify({"error": "Diese Region ist bereits angelegt"}), 409

    region = store.add_region(country, subdivision, label, holidays_only)
    refresh_region(region)
    return jsonify(_region_summary(region)), 201


@app.delete("/api/regions/<rid>")
def api_delete_region(rid: str):
    removed = store.delete_region(rid)
    if removed is None:
        return jsonify({"error": "Region nicht gefunden"}), 404
    if publisher:
        publisher.remove_region(removed)
    with _data_lock:
        region_data.pop(rid, None)
    return jsonify({"ok": True})


@app.post("/api/regions/<rid>/refresh")
def api_refresh_region(rid: str):
    region = next((r for r in store.load_regions() if r["id"] == rid), None)
    if region is None:
        return jsonify({"error": "Region nicht gefunden"}), 404
    refresh_region(region)
    return jsonify(_region_summary(region))


# ---------------------------------------------------------------- Start

def main() -> None:
    global publisher  # noqa: PLW0603

    mqtt_host = os.environ.get("MQTT_HOST")
    if mqtt_host:
        publisher = Publisher(
            host=mqtt_host,
            port=int(os.environ.get("MQTT_PORT", "1883")),
            username=os.environ.get("MQTT_USER"),
            password=os.environ.get("MQTT_PASSWORD"),
        )
        publisher.start()
    else:
        _LOGGER.warning("MQTT_HOST nicht gesetzt – es werden keine Entitäten angelegt")

    threading.Thread(target=refresh_all, daemon=True).start()
    threading.Thread(target=_scheduler, daemon=True).start()

    port = int(os.environ.get("PORT", "8099"))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
