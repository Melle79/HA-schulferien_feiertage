# Schulferien & Feiertage Manager (Home Assistant Add-on)

Add-on mit eigener Weboberfläche (Ingress-Panel in der Sidebar), das Schulferien und gesetzliche Feiertage aus frei verfügbaren Open-Data-APIs lädt und als Entitäten via **MQTT Discovery** in Home Assistant anlegt.

## Funktionen

- **Staat → Bundesland → Region** per Dropdown (live aus der API; Unterregionen wie Augsburg erscheinen nur unter ihrem Bundesland)
- **Beliebig viele Regionen** parallel – jede bekommt ein eigenes MQTT-Gerät
- **Wählbare Datenquelle** mit Live-Verfügbarkeitstest und **Fallback-API** (siehe Datenquellen)
- **„Nur Feiertage"-Modus** pro Region: nur Feiertags-Entitäten, Präfix `feiertage_` statt `schulferien_`
- **Kombinierter Modus**: eine einzelne Entität je Region mit allen Daten als Attribute
- **Optionales Suffix** je Region für die Entity-IDs; alle erzeugten IDs zeigt die Infobox „Entitäten" (Klick = kopieren)
- **Übersicht mit Vorschau**: Status-Badges (heute/morgen), 14-Tage-Streifen (Ferien = gelb, Feiertag = blau, Wochenende = grau, heute umrandet) und Terminliste je Region
- **Aktualisierungsintervall wählbar** (12 oder 24 h) plus manueller Refresh je Region
- Statusleiste: Version, API-Verfügbarkeit (Stand der letzten Aktualisierung), MQTT-Status, Zeitpunkt der letzten Aktualisierung
- Regionale Feiertage (z. B. Augsburger Friedensfest) erscheinen nur bei passend angelegter Region
- Tägliche Neuberechnung nach Mitternacht, Konfiguration persistent in `/data/`

## Entitäten pro Region (Standardmodus)

| Entität (object_id-Schema) | Typ | Attribute |
|---|---|---|
| `binary_sensor.schulferien_<name>_heute_schulfrei` | binary_sensor | `datum`, `grund` (Feiertag / Ferien / Wochenende) |
| `binary_sensor.schulferien_<name>_morgen_schulfrei` | binary_sensor | `datum`, `grund` |
| `binary_sensor.schulferien_<name>_heute_feiertag` | binary_sensor | `datum`, `name` |
| `binary_sensor.schulferien_<name>_morgen_feiertag` | binary_sensor | `datum`, `name` |
| `sensor.schulferien_<name>_naechster_feiertag` | sensor | `datum`, `in_tagen` |
| `sensor.schulferien_<name>_naechste_schulferien` | sensor | `beginn`, `ende`, `in_tagen`, `dauer_tage`, `aktuell_ferien` |

Mit Suffix wird dieses an die object_id angehängt (z. B. `…_heute_schulfrei_kinder`).

**Nur Feiertage:** nur die drei Feiertags-Entitäten, Präfix `feiertage_` (z. B. `binary_sensor.feiertage_bayern_heute_feiertag`), Gerätename „Feiertage <Name>".

**Kombiniert:** eine Entität `sensor.schulferien_<name>_status` (bzw. `feiertage_…_status`). State = `Schule` / `Ferien` / `Feiertag` / `Wochenende` (bzw. `Feiertag` / `Kein Feiertag`), alle Detaildaten als Attribute (`heute_schulfrei`, `naechster_feiertag`, `schulferien_beginn`, …).

## Datenquellen (alle ohne API-Key)

| API | Schulferien | Feiertage | Abdeckung |
|---|---|---|---|
| [OpenHolidays API](https://www.openholidaysapi.org) (Standard) | ✅ | ✅ | International inkl. aller deutschen Bundesländer und Unterregionen |
| [ferien-api.de](https://ferien-api.de) + [feiertage-api.de](https://feiertage-api.de) | ✅ | ✅ | Nur Deutschland |
| [Nager.Date](https://date.nager.at) | ❌ | ✅ | International |

Primär- und Fallback-API sind in den Einstellungen wählbar; vor dem Speichern wird die gewählte API live getestet. Fällt die primäre API aus, übernimmt automatisch der Fallback – die genutzte Quelle steht auf jeder Regionskarte.

## Voraussetzungen

- MQTT-Broker (z. B. das offizielle **Mosquitto broker** Add-on) und die **MQTT-Integration** in HA. Das Add-on holt sich die Zugangsdaten automatisch vom Supervisor (`services: mqtt:need`).

## Installation

Unter *Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories* dieses Repository hinzufügen:
`https://github.com/Melle79/HA-schulferien_feiertage`

Dann **Schulferien & Feiertage Manager** installieren, starten und das Panel **„Schulferien"** in der Sidebar öffnen.

## Hinweise

- Die Entitäten erscheinen unter **Einstellungen → Geräte & Dienste → MQTT**, ein Gerät je Region.
- Beim Entfernen einer Region werden die Discovery- und State-Topics geleert; das Gerät verschwindet aus HA.
- States und Discovery werden retained publiziert – Entitäten überleben HA-Neustarts (Verfügbarkeit „offline" bei gestopptem Add-on).
- Zeitfenster der Daten: 14 Tage rückwirkend bis 18 Monate voraus.
- Die Richtigkeit der Daten liegt bei den API-Betreibern – verbindliche Termine bitte über die offiziellen Quellen der Bundesländer prüfen.

## Haftungsausschluss

Dieser Code wurde **vollständig mit KI (Claude von Anthropic) erstellt**. Die Nutzung erfolgt auf eigene Gefahr – **jegliche Haftung ist ausgeschlossen** (MIT-Lizenz). Es findet **kein Support** statt.
