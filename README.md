# HA Schulferien & Feiertage

Home Assistant Add-on-Repository mit dem **Schulferien & Feiertage Manager**: Schulferien und gesetzliche Feiertage von der offiziellen [OpenHolidays API](https://www.openholidaysapi.org) als Entitäten in Home Assistant – verwaltet über eine eigene Weboberfläche.

[![Repository zu Home Assistant hinzufügen](https://img.shields.io/badge/Repository_zu-Home_Assistant_hinzufügen-41BDF5?logo=home-assistant&logoColor=white&style=for-the-badge)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FMelle79%2FHA-schulferien_feiertage)

*Hinweis: Falls der Dialog in HA nicht vorbefüllt erscheint (bekannter my.home-assistant.io-Bug), die Repo-URL einfach manuell unter Add-on Store → ⋮ → Repositories eintragen.*

## Funktionen

- **Web-UI als Ingress-Panel**: Staat → Bundesland → Region per Dropdown wählen (live aus der API; Unterregionen wie Augsburg erscheinen nur unter ihrem Bundesland)
- **Mehrere Regionen** parallel – jede Region wird ein eigenes MQTT-Gerät mit eigenen Entitäten
- **Wählbare APIs ohne Key** mit Verfügbarkeitstest und **Fallback-API**: OpenHolidays API (Standard), ferien-api.de + feiertage-api.de (nur DE), Nager.Date (nur Feiertage)
- **„Nur Feiertage"-Modus** pro Region – Entitäten heißen dann `feiertage_…` statt `schulferien_…`
- **Kombinierter Modus**: wahlweise eine einzelne Entität je Region mit allen Daten als Attribute
- **Eigenes Suffix** pro Region für die Entity-IDs; alle erzeugten Entitäten werden in der UI in einer Infobox angezeigt (Klick = kopieren)
- **Aktualisierungsintervall wählbar** (12 oder 24 h) plus manueller Refresh; Status zeigt API-Verfügbarkeit und Zeitpunkt der letzten Aktualisierung
- Regionale Feiertage (z. B. Augsburger Friedensfest) erscheinen nur, wenn die passende Region angelegt ist
- Entitäten via **MQTT Discovery** (retained), automatischer Cleanup beim Entfernen einer Region

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

## Haftungsausschluss

Dieser Code wurde **vollständig mit KI (Claude von Anthropic) erstellt**. Die Nutzung erfolgt auf eigene Gefahr – **jegliche Haftung ist ausgeschlossen** (siehe auch MIT-Lizenz). Es findet **kein Support** statt; Issues und Pull Requests werden möglicherweise nicht beantwortet.
