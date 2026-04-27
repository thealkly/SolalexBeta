#!/usr/bin/with-contenv bashio
# Manual entry point (e.g. `docker run ... /run.sh`).
# The canonical service launch lives in addon/rootfs/etc/services.d/solalex/run;
# this script stays aligned with it on purpose — same Python env, same flags.
set -euo pipefail

bashio::log.info "Starting Solalex backend (manual entry)..."

cd /opt/solalex

export SOLALEX_DB_PATH="${SOLALEX_DB_PATH:-/data/solalex.db}"
export SOLALEX_PORT="${SOLALEX_PORT:-8099}"
export PYTHONPATH="/opt/solalex/src:${PYTHONPATH:-}"

exec /opt/solalex/.venv/bin/uvicorn solalex.main:app \
    --host 0.0.0.0 \
    --port "${SOLALEX_PORT}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
