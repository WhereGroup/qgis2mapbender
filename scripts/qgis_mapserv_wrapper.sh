#!/bin/bash
set -eu

source /data/bin/qgisserver.env

: "${QGIS_DB_SERVICE:?QGIS_DB_SERVICE is required}"
: "${QGIS_SERVER_BASE_URL:?QGIS_SERVER_BASE_URL is required}"
: "${QGIS_SERVER_FCGI:?QGIS_SERVER_FCGI is required}"
: "${PGSERVICEFILE:?PGSERVICEFILE is required}"

export PGSERVICEFILE
unset PGPASSFILE
unset PGPASSWORD

extract_param() {
    echo "$QUERY_STRING" | tr '&' '\n' | grep "^$1=" | head -1 | cut -d= -f2-
}

PROJECT=$(extract_param "map")
SCHEMA=$(extract_param "schema")

if [ -z "$PROJECT" ] || [ -z "$SCHEMA" ]; then
    printf 'Status: 400 Bad Request\r\n'
    printf 'Content-Type: text/plain\r\n\r\n'
    printf 'Both map and schema parameters are required.\n'
    exit 1
fi

REMAINING=$(echo "$QUERY_STRING" \
    | tr '&' '\n' \
    | grep -v "^map=" \
    | grep -v "^schema=" \
    | tr '\n' '&' \
    | sed 's/&$//')

DB_URI="postgresql://?service=${QGIS_DB_SERVICE}%26schema=${SCHEMA}%26project=${PROJECT}"

if [ -n "$REMAINING" ]; then
    export QUERY_STRING="map=${DB_URI}&${REMAINING}"
else
    export QUERY_STRING="map=${DB_URI}"
fi

export QGIS_SERVER_WMS_SERVICE_URL="${QGIS_SERVER_BASE_URL}?map=${PROJECT}&schema=${SCHEMA}&"

exec "$QGIS_SERVER_FCGI"
