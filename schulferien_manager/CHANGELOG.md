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

## 1.1.2

- Fix: Entitäten wurden nicht angelegt, wenn publiziert wurde, bevor die MQTT-Verbindung stand (z. B. direkt nach Add-on-Start/-Update). Publishes laufen jetzt mit QoS 1 (werden gepuffert), zusätzlich werden nach jedem (Re-)Connect alle Regionen automatisch neu publiziert.

## 1.1.3

- Fix: Entity-IDs mit Umlauten im Namen (Nächster Feiertag, Nächste Schulferien) wichen von den angezeigten IDs ab, weil HA das veraltete `object_id` seit Core 2026.4 ignoriert. Discovery nutzt jetzt `default_entity_id` (benötigt HA Core ≥ 2025.10).
- Fix: Kopieren der Entity-IDs funktioniert jetzt auch im Ingress-Panel (HTTP) per Fallback; sichtbare Rückmeldung "✓ in Zwischenablage kopiert" bzw. Fehlerhinweis.

## 1.2.0

- Neues Attribut `vorschau` (14-Tage-Status) an "Nächster Feiertag" bzw. der kombinierten Status-Entität
- Custom Lovelace Card `schulferien-card` im Repo (www/schulferien-card.js): Badges, 14-Tage-Streifen, nächste Termine; unterstützt alle Modi inkl. Suffix

## 1.2.1

- Neue Attribute `aktuell_ferien_beginn` und `aktuell_ferien_ende` an "Nächste Schulferien" bzw. der kombinierten Entität (für den Ferien-Banner der Schulferien Card)
