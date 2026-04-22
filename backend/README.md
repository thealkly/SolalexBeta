# Solalex Backend

Python 3.13 + FastAPI + raw `aiosqlite`. Managed with [`uv`](https://docs.astral.sh/uv/).

## Setup

```bash
cd backend
uv sync
```

## Run (local dev)

```bash
uv run uvicorn solalex.main:app --reload --port 8099
```

## Tests

```bash
uv run pytest
```
