# HA Schulferien & Feiertage

Home Assistant Add-on-Repository mit dem **Schulferien & Feiertage Manager**: Schulferien und gesetzliche Feiertage aus frei verfügbaren Open-Data-APIs (ohne API-Key) als Entitäten in Home Assistant – verwaltet über eine eigene Weboberfläche mit Vorschau, wählbarer Datenquelle und Fallback-API.

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

Entity-ID-Schema: `schulferien_<name>[_suffix]_<entität>`, z. B. `binary_sensor.schulferien_bayern_heute_schulfrei`.

Besondere Modi:
- **Nur Feiertage**: es werden nur die drei Feiertags-Entitäten angelegt, mit Präfix `feiertage_` statt `schulferien_` (z. B. `binary_sensor.feiertage_bayern_heute_feiertag`).
- **Kombinierte Entität**: eine einzige `sensor`-Entität je Region (`sensor.schulferien_<name>_status`). State = `Schule` / `Ferien` / `Feiertag` / `Wochenende` (bzw. `Feiertag` / `Kein Feiertag` bei „Nur Feiertage"), alle Detaildaten liegen in den Attributen.
- **Suffix**: optionaler Namenszusatz je Region für eindeutige Entity-IDs; die tatsächlich erzeugten IDs zeigt die Infobox „Entitäten" auf der Regionskarte (Klick = kopieren).

## Voraussetzungen

- Home Assistant Core **2025.10 oder neuer** (Discovery nutzt `default_entity_id`)
- MQTT-Broker (z. B. das offizielle **Mosquitto broker** Add-on) und die MQTT-Integration in Home Assistant. Die Zugangsdaten holt sich das Add-on automatisch vom Supervisor.

## Installation

1. Badge oben anklicken **oder** unter *Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories* diese URL hinzufügen:
   `https://github.com/Melle79/HA-schulferien_feiertage`
2. **Schulferien & Feiertage Manager** installieren und starten.
3. Panel **„Schulferien"** in der Sidebar öffnen und Regionen anlegen.

## Dashboard-Karte

Im Ordner [`dist/`](dist/) liegt eine Custom Lovelace Card (`schulferien-card.js`) im Stil des Add-on-Panels: Status-Badges, 14-Tage-Streifen und nächste Termine. Sie funktioniert mit allen drei Modi (einzelne Entitäten, „Nur Feiertage", kombinierte Entität).

**Installation über HACS (empfohlen):**
1. HACS → ⋮ (oben rechts) → **Benutzerdefinierte Repositories** → URL `https://github.com/Melle79/HA-schulferien_feiertage`, Typ **Dashboard** → hinzufügen.
2. „Schulferien Card" suchen und installieren – HACS trägt die Ressource automatisch ein und liefert künftige Updates mit.
3. Browser-Cache leeren und Karte einfügen (siehe unten).

**Manuelle Installation (Alternative):**
1. `dist/schulferien-card.js` nach `/config/www/` kopieren.
2. *Einstellungen → Dashboards → ⋮ → Ressourcen* → `/local/schulferien-card.js` als **JavaScript-Modul** hinzufügen (danach Browser-Cache leeren).
3. Karte einfügen:

```yaml
type: custom:schulferien-card
title: Schulferien Bayern
prefix: schulferien_bayern   # bzw. feiertage_bayern bei "Nur Feiertage"
# suffix: kinder             # optional, falls beim Anlegen vergeben
# show_strip: false          # 14-Tage-Streifen ausblenden
```

Der `prefix` ist der Teil der Entity-IDs vor dem Entitätsnamen – einfach aus der Infobox „Entitäten" im Add-on ablesen (z. B. `binary_sensor.schulferien_bayern_heute_schulfrei` → `schulferien_bayern`). Voraussetzung ist Add-on-Version ≥ 1.2.0 (liefert das `vorschau`-Attribut für den Tagesstreifen).

## Datenquellen

Alle Datenquellen sind frei nutzbar und benötigen **keinen API-Key**. Primär- und Fallback-API sind in den Einstellungen des Add-ons wählbar; vor dem Speichern wird die Verfügbarkeit live getestet.

| API | Schulferien | Feiertage | Abdeckung | Link |
|---|---|---|---|---|
| **OpenHolidays API** (Standard) | ✅ | ✅ | International, u. a. alle deutschen Bundesländer inkl. Unterregionen (z. B. Augsburg) | [openholidaysapi.org](https://www.openholidaysapi.org) |
| **ferien-api.de + feiertage-api.de** | ✅ | ✅ | Nur Deutschland | [ferien-api.de](https://ferien-api.de) · [feiertage-api.de](https://feiertage-api.de) |
| **Nager.Date** | ❌ | ✅ | International (über 100 Länder) | [date.nager.at](https://date.nager.at) |

Fällt die primäre API beim Datenabruf aus, übernimmt automatisch die konfigurierte Fallback-API; die genutzte Quelle wird auf jeder Regionskarte unter „Quelle:" angezeigt. Die Daten werden je nach Einstellung alle 12 oder 24 Stunden aktualisiert (Zeitfenster: 14 Tage rückwirkend bis 18 Monate voraus), zusätzlich ist ein manueller Refresh pro Region möglich.

*Hinweis: Die Richtigkeit und Vollständigkeit der Daten liegt bei den jeweiligen API-Betreibern – für verbindliche Termine bitte die offiziellen Quellen der Bundesländer prüfen.*

## Lizenz

MIT – siehe [LICENSE](LICENSE).

## Haftungsausschluss

Dieser Code wurde **vollständig mit KI erstellt**. Die Nutzung erfolgt auf eigene Gefahr – **jegliche Haftung ist ausgeschlossen** (siehe auch MIT-Lizenz). Es findet **kein Support** statt; Issues und Pull Requests werden möglicherweise nicht beantwortet.
