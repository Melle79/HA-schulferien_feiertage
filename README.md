# HA Schulferien & Feiertage

Home Assistant Add-on-Repository mit dem **Schulferien & Feiertage Manager**: Schulferien und gesetzliche Feiertage von der offiziellen [OpenHolidays API](https://www.openholidaysapi.org) als Entitäten in Home Assistant – verwaltet über eine eigene Weboberfläche.

[![Repository zu Home Assistant hinzufügen](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FMelle79%2FHA-schulferien_feiertage)

## Funktionen

- **Web-UI als Ingress-Panel**: Staat → Bundesland → Region per Dropdown wählen (live aus der OpenHolidays API)
- **Mehrere Regionen** parallel – jede Region wird ein eigenes MQTT-Gerät mit eigenen Entitäten
- **„Nur Feiertage"-Modus** pro Region (legt keine Schulferien-Entitäten an)
- **Übersicht mit Vorschau**: Status-Badges (heute/morgen), 14-Tage-Streifen und Terminliste je Region
- Entitäten via **MQTT Discovery** (retained), automatischer Cleanup beim Entfernen einer Region
- API-Refresh alle 12 h, Zustands-Neuberechnung nach Mitternacht

## Entitäten pro Region

| Entität | Typ | Attribute |
|---|---|---|
| Heute schulfrei | binary_sensor | `datum`, `grund` (Feiertag / Ferien / Wochenende) |
| Morgen schulfrei | binary_sensor | `datum`, `grund` |
| Heute Feiertag | binary_sensor | `datum`, `name` |
| Morgen Feiertag | binary_sensor | `datum`, `name` |
| Nächster Feiertag | sensor | `datum`, `in_tagen` |
| Nächste Schulferien | sensor | `beginn`, `ende`, `in_tagen`, `dauer_tage`, `aktuell_ferien` |

Im Modus „Nur Feiertage" werden nur die drei Feiertags-Entitäten angelegt.

## Voraussetzungen

- MQTT-Broker (z. B. das offizielle **Mosquitto broker** Add-on) und die MQTT-Integration in Home Assistant. Die Zugangsdaten holt sich das Add-on automatisch vom Supervisor.

## Installation

1. Badge oben anklicken **oder** unter *Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories* diese URL hinzufügen:
   `https://github.com/Melle79/HA-schulferien_feiertage`
2. **Schulferien & Feiertage Manager** installieren und starten.
3. Panel **„Schulferien"** in der Sidebar öffnen und Regionen anlegen.

## Datenquelle

[OpenHolidays API](https://www.openholidaysapi.org) – offenes Open-Data-Projekt mit Schulferien und Feiertagen für Deutschland (alle Bundesländer) und viele weitere Länder. Kein API-Key erforderlich.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
