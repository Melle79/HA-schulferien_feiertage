"""MQTT Discovery: legt pro Region ein Gerät mit Entitäten in Home Assistant an."""
from __future__ import annotations

import json
import logging
import threading

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)

DISCOVERY_PREFIX = "homeassistant"
BASE_TOPIC = "schulferien"
AVAILABILITY_TOPIC = f"{BASE_TOPIC}/availability"

# (component, key, anzeigename, icon)
ENTITY_DEFS_FULL = [
    ("binary_sensor", "heute_schulfrei", "Heute schulfrei", "mdi:school-outline"),
    ("binary_sensor", "morgen_schulfrei", "Morgen schulfrei", "mdi:school-outline"),
    ("binary_sensor", "heute_feiertag", "Heute Feiertag", "mdi:calendar-star"),
    ("binary_sensor", "morgen_feiertag", "Morgen Feiertag", "mdi:calendar-star"),
    ("sensor", "naechster_feiertag", "Nächster Feiertag", "mdi:calendar-star"),
    ("sensor", "naechste_schulferien", "Nächste Schulferien", "mdi:beach"),
]
ENTITY_DEFS_HOLIDAYS_ONLY = [
    ("binary_sensor", "heute_feiertag", "Heute Feiertag", "mdi:calendar-star"),
    ("binary_sensor", "morgen_feiertag", "Morgen Feiertag", "mdi:calendar-star"),
    ("sensor", "naechster_feiertag", "Nächster Feiertag", "mdi:calendar-star"),
]


def entity_defs(holidays_only: bool) -> list:
    return ENTITY_DEFS_HOLIDAYS_ONLY if holidays_only else ENTITY_DEFS_FULL


class Publisher:
    """Verwaltet die MQTT-Verbindung und veröffentlicht Discovery + Zustände."""

    def __init__(self, host: str, port: int, username: str | None, password: str | None):
        self.connected = threading.Event()
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id="schulferien-manager"
        )
        if username:
            self._client.username_pw_set(username, password or "")
        self._client.will_set(AVAILABILITY_TOPIC, "offline", retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._host = host
        self._port = port

    def start(self) -> None:
        try:
            self._client.connect_async(self._host, self._port, keepalive=60)
            self._client.loop_start()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("MQTT-Verbindung fehlgeschlagen: %s", err)

    def stop(self) -> None:
        try:
            self._client.publish(AVAILABILITY_TOPIC, "offline", retain=True)
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:  # noqa: BLE001
            pass

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            _LOGGER.info("Mit MQTT-Broker verbunden")
            client.publish(AVAILABILITY_TOPIC, "online", retain=True)
            self.connected.set()
        else:
            _LOGGER.error("MQTT-Verbindung abgelehnt: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        _LOGGER.warning("MQTT-Verbindung getrennt (%s)", reason_code)
        self.connected.clear()

    # ---------- Discovery ----------

    def publish_discovery(self, region: dict) -> None:
        rid = region["id"]
        device = {
            "identifiers": [f"schulferien_{rid}"],
            "name": f"Schulferien {region['label']}",
            "manufacturer": "OpenHolidays API",
            "model": region.get("subdivision") or region.get("country", ""),
            "sw_version": "1.0.0",
        }
        slug = _slugify(region["label"])
        for component, key, name, icon in entity_defs(region.get("holidays_only", False)):
            config_topic = f"{DISCOVERY_PREFIX}/{component}/schulferien_{rid}/{key}/config"
            payload = {
                "name": name,
                "unique_id": f"schulferien_{rid}_{key}",
                "object_id": f"{slug}_{key}",
                "state_topic": f"{BASE_TOPIC}/{rid}/{key}/state",
                "json_attributes_topic": f"{BASE_TOPIC}/{rid}/{key}/attributes",
                "availability_topic": AVAILABILITY_TOPIC,
                "icon": icon,
                "device": device,
            }
            self._client.publish(config_topic, json.dumps(payload), retain=True)
        _LOGGER.info("Discovery veröffentlicht für Region %s (%s)", region["label"], rid)

    def publish_states(self, region: dict, states: dict) -> None:
        rid = region["id"]
        for key, value in states.items():
            self._client.publish(
                f"{BASE_TOPIC}/{rid}/{key}/state", value["state"], retain=True
            )
            self._client.publish(
                f"{BASE_TOPIC}/{rid}/{key}/attributes",
                json.dumps(value["attributes"], ensure_ascii=False),
                retain=True,
            )

    def remove_region(self, region: dict) -> None:
        """Discovery- und State-Topics einer Region löschen (leere retained Payloads)."""
        rid = region["id"]
        for component, key, _name, _icon in ENTITY_DEFS_FULL:
            self._client.publish(
                f"{DISCOVERY_PREFIX}/{component}/schulferien_{rid}/{key}/config",
                "",
                retain=True,
            )
            self._client.publish(f"{BASE_TOPIC}/{rid}/{key}/state", "", retain=True)
            self._client.publish(f"{BASE_TOPIC}/{rid}/{key}/attributes", "", retain=True)
        _LOGGER.info("Region %s aus MQTT entfernt", rid)


def _slugify(text: str) -> str:
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
    for src, dst in repl.items():
        text = text.replace(src, dst)
    out = "".join(c if c.isalnum() else "_" for c in text.lower())
    while "__" in out:
        out = out.replace("__", "_")
    return f"schulferien_{out.strip('_')}"
