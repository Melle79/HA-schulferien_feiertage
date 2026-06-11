# Schulferien & Feiertage Manager (Home Assistant Add-on)

Add-on mit eigener Weboberfläche (Ingress-Panel in der Sidebar), das Schulferien und gesetzliche Feiertage von der offiziellen **OpenHolidays API** (openholidaysapi.org) lädt und als Entitäten via **MQTT Discovery** in Home Assistant anlegt.

## Funktionen

- **Staat → Bundesland → Region** per Dropdown wählbar (live aus der API geladen; eine dritte Ebene erscheint nur, wenn das Land Unterregionen hat)
- **Beliebig viele Regionen** parallel – jede bekommt ein eigenes MQTT-Gerät mit eigenen Entitäten
- **„Nur Feiertage"-Modus** pro Region: legt nur die Feiertags-Entitäten an, keine Schulferien
- **Übersicht mit Vorschau**: pro Region Status-Badges (heute/morgen), ein 14-Tage-Streifen (Ferien = gelb, Feiertag = blau, Wochenende = grau, heute umrandet) und die Liste der nächsten Termine
- Tägliche Neuberechnung nach Mitternacht, API-Refresh alle 12 h, Konfiguration persistent in `/data/regions.json`

## Entitäten pro Region

| Entität (object_id-Schema) | Typ | Attribute |
|---|---|---|
| `binary_sensor.schulferien_<name>_heute_schulfrei` | binary_sensor | `datum`, `grund` (Feiertag/Ferien/Wochenende) |
| `binary_sensor.schulferien_<name>_morgen_schulfrei` | binary_sensor | `datum`, `grund` |
| `binary_sensor.schulferien_<name>_heute_feiertag` | binary_sensor | `datum`, `name` |
| `binary_sensor.schulferien_<name>_morgen_feiertag` | binary_sensor | `datum`, `name` |
| `sensor.schulferien_<name>_naechster_feiertag` | sensor | `datum`, `in_tagen` |
| `sensor.schulferien_<name>_naechste_schulferien` | sensor | `beginn`, `ende`, `in_tagen`, `dauer_tage`, `aktuell_ferien` |

Im Modus „Nur Feiertage" werden ausschließlich die drei Feiertags-Entitäten angelegt.

## Voraussetzungen

- MQTT-Broker (z. B. das offizielle **Mosquitto broker** Add-on) und die **MQTT-Integration** in HA. Das Add-on holt sich die Zugangsdaten automatisch vom Supervisor (`services: mqtt:need`).

## Installation (lokales Add-on)

```bash
# Ordner auf den HA-Server kopieren (Samba/SSH):
scp -r schulferien_manager root@192.168.0.222:/addons/
```

Dann: **Einstellungen → Add-ons → Add-on Store → ⋮ → Nach Updates suchen** → „Schulferien & Feiertage Manager" unter *Lokale Add-ons* installieren → starten → Panel **„Schulferien"** in der Sidebar öffnen.

## Hinweise

- Die Entitäten erscheinen unter **Einstellungen → Geräte & Dienste → MQTT**, ein Gerät je Region ("Schulferien <Name>").
- Beim Entfernen einer Region in der UI werden die Discovery- und State-Topics geleert; das Gerät verschwindet aus HA.
- States und Discovery werden retained publiziert – Entitäten überleben HA-Neustarts auch bei gestopptem Add-on (mit Verfügbarkeit „offline").
- Zeitfenster der Daten: 14 Tage rückwirkend bis 18 Monate voraus.
