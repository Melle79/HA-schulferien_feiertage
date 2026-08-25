# Schulferien & Feiertage Manager (Home Assistant Add-on)

Add-on mit eigener Weboberfläche (Ingress-Panel in der Sidebar), das Schulferien und gesetzliche Feiertage aus frei verfügbaren Open-Data-APIs lädt und als Entitäten via **MQTT Discovery** in Home Assistant anlegt.

[![Buy Me a Coffee](https://img.shields.io/badge/Buy_me_a_coffee-melle79-FFDD00?logo=buymeacoffee&logoColor=black&style=for-the-badge)](https://buymeacoffee.com/melle79)

## Funktionen

- **Staat → Bundesland → Region** per Dropdown (live aus der API; Unterregionen wie Augsburg erscheinen nur unter ihrem Bundesland)
- **Beliebig viele Regionen** parallel – jede bekommt ein eigenes MQTT-Gerät
- **Wählbare Datenquelle** mit Live-Verfügbarkeitstest und **Fallback-API** (siehe Datenquellen)
- **„Nur Feiertage"-Modus** pro Region: nur Feiertags-Entitäten, Präfix `feiertage_` statt `schulferien_`
- **Kombinierter Modus**: eine einzelne Entität je Region mit allen Daten als Attribute
- **Optionales Suffix** je Region für die Entity-IDs; alle erzeugten IDs zeigt die Infobox „Entitäten" (Klick = kopieren)
- **Übersicht mit Vorschau**: Status-Badges (heute/morgen), 14-Tage-Streifen (Ferien = gelb, Feiertag = blau, Wochenende = grau, heute umrandet) und Terminliste je Region
- **Dashboard-Karte inklusive**: Die *Schulferien Card* wird vom Add-on mitgeliefert, nach `www/schulferien_manager/` kopiert und selbst als Dashboard-Ressource eingetragen – kein HACS nötig (siehe unten)
- **Aktualisierung zu festen Zeiten** (täglich 00:00, optional zusätzlich 12:00 Uhr) plus manueller Refresh je Region; bei API-Fehlern bleiben die letzten Daten erhalten und es wird automatisch erneut versucht
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
| `sensor.schulferien_<name>_kalender` | sensor | `schulferien` (Liste: name, beginn, ende, dauer_tage), `feiertage` (Liste: name, datum), `zeitraum_von`, `zeitraum_bis` – alle Termine für ca. 18 Monate; State = Anzahl der Einträge. Wird in jedem Modus angelegt. |

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

## Dashboard-Karte

Das Add-on bringt die [Schulferien Card](https://github.com/Melle79/HA-schulferien-card) mit und richtet sie beim Start selbst ein: Es kopiert die Datei nach `<config>/www/schulferien_manager/schulferien-card.js` und trägt sie über die WebSocket-API als Dashboard-Ressource (`/local/schulferien_manager/schulferien-card.js`) ein. Danach steht **„Schulferien Card"** in der Kartenauswahl – ein Neuladen des Browsers genügt, HACS wird nicht gebraucht.

Der Stand steht im Panel unter **Dashboard-Karte**; dort lässt sich die Einrichtung auch von Hand erneut anstoßen. Mit jeder neuen Add-on-Version wird die Karte mit aktualisiert, die Ressourcen-URL bekommt dann die neue Versionsnummer angehängt (sonst hielten die Browser die alte Datei bis zu einem Monat im Cache).

Zwei Fälle, in denen sich das Add-on heraushält:

- **Karte bereits über HACS installiert**: Dann verwaltet HACS sie weiter – zwei Quellen für dieselbe Karte wären eine Kollision. Das Panel zeigt das an.
- **Dashboards im YAML-Modus**: Dort verwaltet HA die Ressourcen nicht selbst. Die Datei wird trotzdem bereitgestellt, der Eintrag muss in die `lovelace:`-Konfiguration:
  ```yaml
  lovelace:
    resources:
      - url: /local/schulferien_manager/schulferien-card.js
        type: module
  ```

Abschalten lässt sich das Ganze in den Add-on-Optionen über **`karte_installieren`**. Das Add-on braucht dafür Schreibzugriff auf die HA-Konfiguration (`homeassistant_config:rw`); geschrieben wird ausschließlich in `www/schulferien_manager/`.

## Voraussetzungen

- Home Assistant Core **2025.10 oder neuer** (Discovery nutzt `default_entity_id`)
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
- Nach dem ersten Start mit v1.5.0 einmal den Browser neu laden – vorher kennt das Frontend die Karte noch nicht.
- Die Richtigkeit der Daten liegt bei den API-Betreibern – verbindliche Termine bitte über die offiziellen Quellen der Bundesländer prüfen.

## Haftungsausschluss

Dies ist ein **privates Hobby-Projekt** ohne kommerziellen Hintergrund. Die Nutzung erfolgt auf eigene Gefahr – **jegliche Haftung ist ausgeschlossen** (MIT-Lizenz). Es findet **kein Support** statt.
