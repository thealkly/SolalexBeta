#!/usr/bin/with-contenv bashio
# Legacy entry point. The canonical service launch lives in
# addon/rootfs/etc/services.d/solalex/run — this script is kept for
# out-of-s6 manual invocation (e.g. `docker run ... /run.sh`).
set -euo pipefail

bashio::log.info "Starting Solalex backend (manual entry)..."

export DB_PATH="${DB_PATH:-/data/solalex.db}"
export PORT="${PORT:-8099}"

exec uv run --no-dev uvicorn solalex.main:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --proxy-headers \
    --forwarded-allow-ips "*"
