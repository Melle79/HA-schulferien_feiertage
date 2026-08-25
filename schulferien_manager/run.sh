#!/usr/bin/with-contenv bashio
set -e

if bashio::services.available "mqtt"; then
    export MQTT_HOST="$(bashio::services mqtt 'host')"
    export MQTT_PORT="$(bashio::services mqtt 'port')"
    export MQTT_USER="$(bashio::services mqtt 'username')"
    export MQTT_PASSWORD="$(bashio::services mqtt 'password')"
    bashio::log.info "MQTT-Broker gefunden: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.warning "Kein MQTT-Service verfügbar – Entitäten können nicht angelegt werden!"
fi

if bashio::config.true 'karte_installieren'; then
    export KARTE_INSTALLIEREN="true"
else
    export KARTE_INSTALLIEREN="false"
    bashio::log.info "Automatische Karten-Installation ist abgeschaltet"
fi

export DATA_DIR="/data"
cd /app/backend
exec python3 app.py
