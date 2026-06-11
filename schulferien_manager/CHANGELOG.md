# Changelog

## 1.0.0

- Erste Veröffentlichung
- Web-UI (Ingress): Staat / Bundesland / Region per Dropdown (OpenHolidays API)
- Mehrere Regionen parallel, je Region ein MQTT-Gerät
- "Nur Feiertage"-Modus pro Region
- 14-Tage-Vorschaustreifen + Terminliste pro Region
- Entitäten via MQTT Discovery (retained), Cleanup beim Entfernen
- API-Refresh alle 12 h, Neuberechnung nach Mitternacht
