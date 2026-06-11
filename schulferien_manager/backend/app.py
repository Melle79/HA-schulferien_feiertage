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
import providers
import store
import mqtt_publisher
from mqtt_publisher import Publisher
from version import VERSION

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
_LOGGER = logging.getLogger("schulferien")

FETCH_PAST_DAYS = 14
FETCH_FUTURE_DAYS = 540

app = Flask(__name__, static_folder="../frontend", static_url_path="")

# rid -> {"school": [...], "public": [...], "fetched": ts, "error": str|None}
region_data: dict[str, dict] = {}
_data_lock = threading.Lock()

publisher: Publisher | None = None


# ---------------------------------------------------------------- Daten laden

def _fetch_with_fallback(kind: str, region: dict, valid_from: date, valid_to: date) -> tuple[list, str]:
    """Zeiträume über Primär- und ggf. Fallback-Provider laden. Liefert (periods, provider_id)."""
    settings = store.load_settings()
    order = [settings["api_provider"]]
    fallback = settings.get("api_fallback", "none")
    if fallback not in ("none", order[0]):
        order.append(fallback)

    last_err: Exception | None = None
    for pid in order:
        if not providers.supports(pid, kind, region["country"]):
            continue
        try:
            periods = providers.fetch_periods(
                pid, kind, region["country"], region.get("subdivision", ""),
                region.get("language", "DE"), valid_from, valid_to,
            )
            if pid != order[0]:
                _LOGGER.warning("Region %s/%s: Fallback auf %s", region["label"], kind, pid)
            return periods, pid
        except Exception as err:  # noqa: BLE001
            last_err = err
            _LOGGER.warning("Region %s/%s: Provider %s fehlgeschlagen: %s",
                            region["label"], kind, pid, err)
    if last_err is not None:
        raise last_err
    return [], ""  # kein Provider zuständig (z. B. Schulferien bei Nager)


def refresh_region(region: dict) -> dict:
    """API-Daten für eine Region laden, Zustände berechnen und publizieren."""
    rid = region["id"]
    today = date.today()
    valid_from = today - timedelta(days=FETCH_PAST_DAYS)
    valid_to = today + timedelta(days=FETCH_FUTURE_DAYS)

    entry = {"school": [], "public": [], "fetched": time.time(), "error": None, "api_used": {}}
    try:
        entry["public"], pid = _fetch_with_fallback("public", region, valid_from, valid_to)
        entry["api_used"]["public"] = pid

        if not region.get("holidays_only", False):
            entry["school"], pid = _fetch_with_fallback("school", region, valid_from, valid_to)
            entry["api_used"]["school"] = pid
        _LOGGER.info(
            "Region %s: %d Feiertage, %d Ferienzeiträume geladen (%s)",
            region["label"], len(entry["public"]), len(entry["school"]),
            entry["api_used"],
        )
    except Exception as err:  # noqa: BLE001
        entry["error"] = str(err)
        _LOGGER.error("Region %s: API-Fehler: %s", region["label"], err)

    with _data_lock:
        region_data[rid] = entry

    if publisher and entry["error"] is None:
        publisher.publish_discovery(region)
        publisher.publish_states(region, _states_for_publish(region, entry))
    return entry


def _states_for_publish(region: dict, entry: dict) -> dict:
    if region.get("combined", False):
        return {"status": logic.build_combined_state(region, entry)}
    return logic.build_states(region, entry)


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
                        publisher.publish_states(region, _states_for_publish(region, entry))

            for region in regions:
                with _data_lock:
                    entry = region_data.get(region["id"])
                interval = store.load_settings()["update_interval_hours"] * 3600
                if entry is None or now - entry["fetched"] > interval:
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


def _nest_subdivisions(subs: list[dict], country: str) -> list[dict]:
    """Hierarchie strikt über Code-Präfixe aufbauen.

    Stellt sicher, dass Unterregionen (z. B. DE-BY-A Augsburg) nur unter ihrem
    tatsächlichen Bundesland erscheinen.
    """
    prefix_len = country.count("-") + 1
    tops = [s for s in subs if s["code"].count("-") <= prefix_len]
    deeper = [s for s in subs if s["code"].count("-") > prefix_len]

    for top in tops:
        # API-children nur behalten, wenn der Code wirklich zum Parent gehört
        top["children"] = [
            c for c in top.get("children", [])
            if c["code"].upper().startswith(top["code"].upper() + "-")
        ]
    for child in deeper:
        parent = next(
            (t for t in tops if child["code"].upper().startswith(t["code"].upper() + "-")),
            None,
        )
        if parent is not None and all(
            c["code"] != child["code"] for c in parent["children"]
        ):
            parent["children"].append(child)
    for top in tops:
        top["children"].sort(key=lambda c: c["name"])
    return tops


def _region_summary(region: dict) -> dict:
    with _data_lock:
        entry = region_data.get(region["id"])
    summary = dict(region)
    summary["entities"] = mqtt_publisher.entity_list(region)
    if entry is None:
        summary.update({"loaded": False, "error": None, "states": {},
                        "preview": [], "day_strip": [], "fetched": None, "api_used": {}})
        return summary
    ok = entry["error"] is None
    summary.update(
        {
            "loaded": ok,
            "error": entry["error"],
            "fetched": entry["fetched"],
            "api_used": entry.get("api_used", {}),
            "states": logic.build_states(region, entry) if ok else {},
            "preview": logic.build_preview(entry, region.get("holidays_only", False)) if ok else [],
            "day_strip": logic.build_day_strip(entry, region.get("holidays_only", False)) if ok else [],
        }
    )
    return summary


# ---------------------------------------------------------------- Routen

@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/status")
def api_status():
    regions = store.load_regions()
    settings = store.load_settings()
    with _data_lock:
        entries = [region_data.get(r["id"]) for r in regions]
    fetched = [e["fetched"] for e in entries if e]
    errors = [e["error"] for e in entries if e and e["error"]]
    api_ok = None
    if entries and all(e is not None for e in entries):
        api_ok = len(errors) == 0
    return jsonify(
        {
            "version": VERSION,
            "mqtt_connected": bool(publisher and publisher.connected.is_set()),
            "mqtt_configured": publisher is not None,
            "regions": len(regions),
            "last_refresh": max(fetched) if fetched else None,
            "api_ok": api_ok,
            "api_errors": errors,
            "settings": settings,
            "provider_name": providers.PROVIDERS.get(settings["api_provider"], {}).get("name"),
        }
    )


@app.get("/api/settings")
def api_get_settings():
    return jsonify(
        {"settings": store.load_settings(), "providers": providers.provider_catalog()}
    )


@app.put("/api/settings")
def api_put_settings():
    body = request.get_json(force=True, silent=True) or {}
    pid = body.get("api_provider", "openholidays")
    if pid not in providers.PROVIDERS:
        return jsonify({"error": f"Unbekannte API: {pid}"}), 400
    fallback = body.get("api_fallback", "none")
    if fallback != "none" and fallback not in providers.PROVIDERS:
        return jsonify({"error": f"Unbekannte Fallback-API: {fallback}"}), 400

    # Verfügbarkeit der gewählten API vor dem Speichern testen
    result = providers.test_provider(pid)
    if not result["ok"]:
        return jsonify({"error": f"API-Test fehlgeschlagen – nicht gespeichert. {result['message']}"}), 409

    saved = store.save_settings(
        {
            "update_interval_hours": int(body.get("update_interval_hours", 12)),
            "api_provider": pid,
            "api_fallback": fallback,
        }
    )
    threading.Thread(target=refresh_all, daemon=True).start()
    return jsonify({"settings": saved, "test": result})


@app.post("/api/providers/test")
def api_test_provider():
    body = request.get_json(force=True, silent=True) or {}
    return jsonify(providers.test_provider(body.get("provider", "")))


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
        return jsonify(_nest_subdivisions(subs, country.upper()))
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
    combined = bool(body.get("combined", False))
    suffix = mqtt_publisher.suffix_slug(str(body.get("suffix", "")))

    if not country:
        return jsonify({"error": "Land fehlt"}), 400
    if not label:
        label = subdivision or country

    for existing in store.load_regions():
        if (
            existing["country"] == country
            and existing.get("subdivision", "") == subdivision
            and existing.get("holidays_only", False) == holidays_only
            and existing.get("combined", False) == combined
            and existing.get("suffix", "") == suffix
        ):
            return jsonify({"error": "Diese Region ist bereits angelegt"}), 409

    region = store.add_region(
        country, subdivision, label, holidays_only, combined=combined, suffix=suffix
    )
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
