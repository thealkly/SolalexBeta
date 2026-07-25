#!/usr/bin/with-contenv bashio
# Manual entry point (e.g. `docker run ... /run.sh`).
# The canonical service launch lives in addon/rootfs/etc/services.d/soalex/run;
# this script stays aligned with it on purpose — same Python env, same flags.
set -euo pipefail

bashio::log.info "Starting Soalex backend (manual entry)..."

cd /opt/soalex

export SOALEX_DB_PATH="${SOALEX_DB_PATH:-/data/soalex.db}"
export SOALEX_PORT="${SOALEX_PORT:-8777}"
export PYTHONPATH="/opt/soalex/src:${PYTHONPATH:-}"

exec /opt/soalex/.venv/bin/uvicorn soalex.main:app \
    --host 0.0.0.0 \
    --port "${SOALEX_PORT}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
