# Changelog

## 1.0.0

- Erste Veröffentlichung
- Web-UI (Ingress): Staat / Bundesland / Region per Dropdown (OpenHolidays API)
- Mehrere Regionen parallel, je Region ein MQTT-Gerät
- "Nur Feiertage"-Modus pro Region
- 14-Tage-Vorschaustreifen + Terminliste pro Region
- Entitäten via MQTT Discovery (retained), Cleanup beim Entfernen
- API-Refresh alle 12 h, Neuberechnung nach Mitternacht

## 1.0.1

- Vorschau auf volle Seitenbreite: eine Regionskarte pro Zeile
- 14-Tage-Streifen größer, mit Wochentag unter jedem Tag

## 1.1.0

- Wählbare APIs (ohne Key) mit Verfügbarkeitstest vor dem Speichern + Fallback-API: OpenHolidays, ferien-api.de + feiertage-api.de, Nager.Date
- Aktualisierungsintervall wählbar (12/24 h)
- Statusleiste: Version, API-Verfügbarkeit (Stand der letzten Aktualisierung) und Zeitpunkt der letzten Aktualisierung
- Pro Region wählbar: einzelne Entitäten oder eine kombinierte Entität (alle Daten als Attribute)
- Optionales Suffix für Entity-IDs; Entitäten-Infobox je Region (Klick = kopieren)
- "Nur Feiertage" als Dropdown (Standard: Nein); Entitäten heißen dann feiertage_… statt schulferien_…
- Unterregionen erscheinen nur noch unter ihrem Bundesland (Augsburg-Fix)
- Regionale Feiertage (z. B. Friedensfest) nur noch bei passender Region
- README: Badge auf shields.io umgestellt, Haftungsausschluss ergänzt

## 1.1.1

- Dokumentation überarbeitet: Datenquellen-Übersicht (alle drei APIs), Entity-Naming-Schema, kombinierter Modus, Suffix
