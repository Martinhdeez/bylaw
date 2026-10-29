# Bylaw: FastAPI app (contract C9) serving the built web UI, on port 8000.
# MODEL_API_KEY is never baked in: it comes from the env file at run time (docker-compose.yml).

FROM node:22.22.0-bookworm-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12.13-slim-bookworm AS app
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /usr/local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# tau2-bench pinned exactly as `make setup` does it (pyproject.toml takes it as an editable path source).
ARG TAU2_REPO=https://github.com/sierra-research/tau2-bench.git
ARG TAU2_COMMIT=0c69df456a96aa76a1162591574dad9c427a34d7
RUN git init -q .context/tau2-bench \
    && git -C .context/tau2-bench fetch -q --depth 1 $TAU2_REPO $TAU2_COMMIT \
    && git -C .context/tau2-bench checkout -q FETCH_HEAD \
    && rm -rf .context/tau2-bench/.git
ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY bylaw/ bylaw/
RUN uv sync --frozen --no-dev
# Vendored demo target (VN1, MIT), imported as `targets.cs_demo` from /app (the editable install's root).
COPY targets/ targets/

FROM python:3.12.13-slim-bookworm
WORKDIR /app
COPY --from=app /app /app
COPY --from=web /web/dist web/dist
ENV PATH=/app/.venv/bin:$PATH \
    TAU2_DATA_DIR=/app/.context/tau2-bench/data \
    BYLAW_REPORTS_DIR=/app/reports \
    BYLAW_RATIFIED_DIR=/app/ratified \
    BYLAW_CACHE_DIR=/app/.cache/reports
EXPOSE 8000
CMD ["uvicorn", "bylaw.api:app", "--host", "0.0.0.0", "--port", "8000"]
