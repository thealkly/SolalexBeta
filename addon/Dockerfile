# syntax=docker/dockerfile:1.7

# Global build arg — must live above the first FROM to be referenced in any
# later FROM line (Docker scoping rule). Default is the amd64 base; the CI
# matrix overrides this per-arch.
ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.13-alpine3.19

# ----- Stage 1: frontend build -----
# Builds the Svelte 5 / Vite 7 SPA into frontend/dist/.
# Runs on the build host arch; produces static assets consumed by the runtime stage.
# Node 22 matches the version used in .github/workflows/*.yml — drift between
# CI and the image has caused "works in CI, breaks in Docker" bugs before.
FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy manifests first for better layer caching.
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

# ----- Stage 2: backend runtime -----
# Targets the multi-arch Home Assistant Python base (amd64 + aarch64 since 2026.03.1).
FROM ${BUILD_FROM} AS backend-runtime

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

# Install uv (Astral) via the official standalone installer.
# s6-overlay + bashio are already provided by the HA base image — do NOT reinstall.
RUN apk add --no-cache curl ca-certificates \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

WORKDIR /opt/solalex

# Copy backend manifest + lockfile first for better layer caching.
COPY backend/pyproject.toml backend/uv.lock* backend/README.md* ./
COPY backend/src/ ./src/

# Install production dependencies only (no dev deps in the image).
RUN uv sync --frozen --no-dev --no-editable

# Copy built frontend from stage 1 into the image.
COPY --from=frontend-builder /app/frontend/dist/ /opt/solalex/frontend_dist/

# s6-overlay service scripts + entrypoint live under addon/rootfs/.
COPY addon/rootfs/ /
RUN chmod a+x /etc/services.d/solalex/run /etc/services.d/solalex/finish

# Labels — HA add-on metadata.
LABEL io.hass.name="Solalex" \
      io.hass.description="Sekundengenaue Nulleinspeisung & Akku-Pool-Steuerung" \
      io.hass.type="addon" \
      io.hass.version="0.1.0" \
      io.hass.arch="amd64|aarch64" \
      maintainer="ALKLY <info@alkly.de>"

# No ports exposed — HA Ingress proxies to the internal port 8099.
