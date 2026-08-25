"""Installiert die Lovelace-Karte und meldet sie als Ressource an.

Damit braucht die Karte kein HACS: das Add-on bringt sie mit, kopiert sie nach
``<ha-config>/www/schulferien_manager/`` und traegt sie ueber die WebSocket-API
als Dashboard-Ressource ein. Geschrieben wird ausschliesslich in diesem einen
Unterordner - der Rest der HA-Konfiguration wird nur gelesen.

Ist die Karte bereits ueber HACS installiert, haelt sich das Add-on heraus:
zwei Quellen fuer dasselbe Custom Element waeren eine Kollision.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading

import websocket  # websocket-client

_LOGGER = logging.getLogger("schulferien.karte")

QUELLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "frontend", "karte", "schulferien-card.js")
UNTERORDNER = "schulferien_manager"
DATEINAME = "schulferien-card.js"
BASIS_URL = f"/local/{UNTERORDNER}/{DATEINAME}"
SUPERVISOR_WS = "ws://supervisor/core/websocket"

# HACS legt seine Repositories hier ab - der Slug der Karte verraet uns,
# ob HACS sie verwaltet.
HACS_SPEICHER = ".storage/hacs.repositories"
HACS_SLUG = "melle79/ha-schulferien-card"

_lock = threading.Lock()
_status: dict = {"aktiv": False, "meldung": "noch nicht geprüft", "version": None,
                 "url": None, "hacs": False}


def status() -> dict:
    with _lock:
        return dict(_status)


def _setze(**werte) -> dict:
    with _lock:
        _status.update(werte)
        return dict(_status)


def config_dir() -> str | None:
    """Pfad, unter dem die HA-Konfiguration im Container eingehaengt ist."""
    for pfad in ("/homeassistant", "/config"):
        if os.path.isdir(pfad):
            return pfad
    return None


def karten_version(pfad: str = QUELLE) -> str | None:
    try:
        with open(pfad, encoding="utf-8") as f:
            kopf = f.read(2000)
    except OSError:
        return None
    treffer = re.search(r'CARD_VERSION\s*=\s*"([^"]+)"', kopf)
    return treffer.group(1) if treffer else None


def _hacs_verwaltet(cfg: str) -> bool:
    """Prueft, ob HACS die Karte installiert hat."""
    pfad = os.path.join(cfg, HACS_SPEICHER)
    try:
        with open(pfad, encoding="utf-8") as f:
            roh = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    return HACS_SLUG in json.dumps(roh).lower()


def _kopieren(cfg: str) -> tuple[str, bool]:
    """Karte nach www/ kopieren. Liefert (Zielpfad, geaendert)."""
    ziel_ordner = os.path.join(cfg, "www", UNTERORDNER)
    ziel = os.path.join(ziel_ordner, DATEINAME)
    os.makedirs(ziel_ordner, exist_ok=True)

    neu = open(QUELLE, "rb").read()
    if os.path.exists(ziel) and open(ziel, "rb").read() == neu:
        return ziel, False

    tmp = ziel + ".tmp"
    with open(tmp, "wb") as f:
        f.write(neu)
    os.replace(tmp, ziel)
    # Eine alte .gz wuerde HA bevorzugt ausliefern - also mit entfernen.
    if os.path.exists(ziel + ".gz"):
        os.remove(ziel + ".gz")
    return ziel, True


def _ws_aufruf(ws, ident: int, nachricht: dict) -> dict:
    ws.send(json.dumps({"id": ident, **nachricht}))
    while True:
        antwort = json.loads(ws.recv())
        if antwort.get("id") == ident:
            return antwort


def _ressource_eintragen(url: str) -> str:
    """Ressource anlegen oder eine vorhandene auf die neue URL umbiegen."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN fehlt – 'homeassistant_api' im Add-on aktiv?")

    ws = websocket.create_connection(SUPERVISOR_WS, timeout=15)
    try:
        if json.loads(ws.recv()).get("type") != "auth_required":
            raise RuntimeError("unerwartete Begrüßung von Home Assistant")
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(ws.recv()).get("type") != "auth_ok":
            raise RuntimeError("Anmeldung an der HA-WebSocket-API abgelehnt")

        antwort = _ws_aufruf(ws, 1, {"type": "lovelace/resources"})
        if not antwort.get("success"):
            fehler = (antwort.get("error") or {}).get("message", "unbekannt")
            raise RuntimeError(f"Ressourcen nicht lesbar ({fehler}) – "
                               "Dashboards im YAML-Modus verwalten ihre Ressourcen selbst")

        vorhanden = [r for r in antwort["result"] if DATEINAME in r.get("url", "")]
        if any(r["url"] == url for r in vorhanden):
            return "unverändert"

        if vorhanden:
            # Eine zweite Ressource fuer dieselbe Karte wuerde kollidieren.
            ziel = vorhanden[0]
            ergebnis = _ws_aufruf(ws, 2, {"type": "lovelace/resources/update",
                                          "resource_id": ziel["id"],
                                          "res_type": ziel.get("type", "module"),
                                          "url": url})
            was = "aktualisiert"
        else:
            ergebnis = _ws_aufruf(ws, 2, {"type": "lovelace/resources/create",
                                          "res_type": "module", "url": url})
            was = "angelegt"
        if not ergebnis.get("success"):
            fehler = (ergebnis.get("error") or {}).get("message", "unbekannt")
            raise RuntimeError(f"Ressource nicht {was}: {fehler}")
        return was
    finally:
        ws.close()


def installieren() -> dict:
    """Karte bereitstellen und anmelden. Fehler werden nur gemeldet, nie geworfen."""
    if os.environ.get("KARTE_INSTALLIEREN", "true").lower() in ("false", "0", "no"):
        return _setze(aktiv=False, meldung="in den Add-on-Optionen abgeschaltet")

    version = karten_version()
    cfg = config_dir()
    if cfg is None:
        return _setze(aktiv=False, version=version,
                      meldung="HA-Konfiguration nicht eingehängt – Add-on neu starten, "
                              "damit die neue Berechtigung greift")

    if _hacs_verwaltet(cfg):
        return _setze(aktiv=False, version=version, hacs=True,
                      meldung="über HACS installiert – das Add-on hält sich heraus")

    try:
        ziel, geaendert = _kopieren(cfg)
    except OSError as err:
        _LOGGER.warning("Karte konnte nicht kopiert werden: %s", err)
        return _setze(aktiv=False, version=version, meldung=f"Kopieren fehlgeschlagen: {err}")

    url = f"{BASIS_URL}?v={version}" if version else BASIS_URL
    try:
        was = _ressource_eintragen(url)
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("Karte liegt in %s, ist aber nicht eingetragen: %s", ziel, err)
        return _setze(aktiv=False, version=version, url=url,
                      meldung=f"Datei liegt bereit, Ressource nicht eingetragen: {err}")

    if geaendert or was != "unverändert":
        _LOGGER.info("Lovelace-Karte v%s bereitgestellt (%s: %s)", version, was, url)
    return _setze(aktiv=True, version=version, url=url, hacs=False,
                  meldung=f"Version {version} eingerichtet ({was})")
