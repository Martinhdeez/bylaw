# DP1 Container image + docker compose

- `Dockerfile`, three stages:
  - `node:22.22.0-bookworm-slim` runs `npm ci && npm run build` in `web/`, producing `web/dist`;
  - `python:3.12.13-slim-bookworm` with `uv` 0.11.19 (copied from `ghcr.io/astral-sh/uv:0.11.19`) clones tau2-bench at `0c69df456a96aa76a1162591574dad9c427a34d7` into `/app/.context/tau2-bench` (the same `git init` and `fetch --depth 1` steps as `make setup`, then `.git` is removed) and runs `uv sync --frozen --no-dev`. Both tau2 and bylaw are editable installs, so `ROOT` is `/app`;
  - the runtime stage is the same Python image without git or uv. It holds `/app` and `web/dist`, sets `TAU2_DATA_DIR=/app/.context/tau2-bench/data` and runs `uvicorn bylaw.api:app --host 0.0.0.0 --port 8000`.
- `docker-compose.yml` defines one service, `bylaw`, on port 8000:
  - `env_file: [{path: .env, required: false}]`, so the image never holds MODEL_API_KEY;
  - bind mounts `./reports`, `./ratified` and `./.cache` to `/app/...`, with `BYLAW_REPORTS_DIR`, `BYLAW_RATIFIED_DIR` and `BYLAW_CACHE_DIR` pointing at them. `.cache` also holds the Muse response cache (`.cache/llm`, relative to the working directory `/app`);
  - a healthcheck on `/api/domains` that uses the image's Python, since the image has no curl;
  - `restart: unless-stopped`.
- `.dockerignore` excludes `.env`, `.env.*`, `.venv`, `node_modules`, `web/dist`, `.context`, `.scratch`, `.artifacts`, `.cache`, `.git`, `.notes`, `.archived`, `reports` and `ratified`. The stores come in through the mounts, not the image.

Image `bylaw:local`: **268 MB** content (compressed) and **1.84 GB** on disk unpacked (`docker image ls`, Docker 29.5.3, arm64).

## Proof (local Docker Desktop on this Mac, 2026-10-27)

Local quirk: this Docker daemon had run out of address pools, because about 20 leftover `agent-*_default` networks from other worktrees used them up. `docker compose up` failed with "all predefined address pools have been fully subnetted". I left those networks alone. The proof ran with a one-line local override that is not committed (`services.bylaw.network_mode: bridge`, passed as `COMPOSE_FILE=docker-compose.yml:<override>`). A VPS with free pools needs no override.

```
$ docker compose build
 ...
#27 naming to docker.io/library/bylaw:local done
 Image bylaw:local Built

$ docker compose up -d
 Container agent-a789027e774655c41-bylaw-1 Started
$ docker compose ps
NAME                              IMAGE         COMMAND                  SERVICE   STATUS                   PORTS
agent-a789027e774655c41-bylaw-1   bylaw:local   "uvicorn bylaw.api:a…"   bylaw     Up 6 seconds (healthy)   0.0.0.0:8000->8000/tcp
$ curl -s localhost:8000/api/domains
["airline","retail"]
$ curl -s localhost:8000/
HTTP 200 text/html; charset=utf-8
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
$ curl -s -X POST localhost:8000/api/audits -H 'content-type: application/json' \
    -d '{"domain":"airline","use_llm":false,"budget":2000,"amend":false}'
{"id":"dd5fabd7a4c0"} HTTP 202
poll 1..50 (every 5 s): running
poll 51: done
$ curl -s localhost:8000/api/audits/dd5fabd7a4c0   (summarised)
{'id': 'dd5fabd7a4c0', 'domain': 'airline', 'status': 'done', 'error': None,
 'holes': ['G5:00GMVN', 'G5:0QOP4M', 'G5:2HN8UN', 'G5:5K7YMA', 'G1:1ERWZ8', 'G2:1ERWZ8', 'G1:01WQQ7', 'G5:0SZHSV',
           'G5:07S7FC', 'G5:S81ZOT', 'G5:0HUIH5', 'G5:1ERWZ8', 'G5:1KUOX2', 'G5:01WQQ7', 'G5:PIM2PK'],
 'contradictions': 0, 'ambiguities': 2}
$ curl -s localhost:8000/api/audits/dd5fabd7a4c0/events   (last 3)
data: {"phase": "search", "message": "2164 tool calls executed", ..., "tool_calls": 2164, "holes": 0, "t": 251.92}
data: {"phase": "verify", "message": "15 Class A holes, 0 contradictions and 2 ambiguities proven 5/5", ..., "t": 252.18}
data: {"phase": "done", "message": "report stored as airline-dd5fabd7a4c0.json", ..., "holes": 15, "t": 252.18}
$ curl localhost:8000/api/reports/latest?domain=airline  -> 200
$ ls .cache/reports        # host side of the bind mount
airline-dd5fabd7a4c0.json
$ docker image inspect bylaw:local --format '{{json .Config.Env}}'
[PATH, LANG, GPG_KEY (python.org release key), PYTHON_VERSION, PYTHON_SHA256, TAU2_DATA_DIR, BYLAW_REPORTS_DIR, BYLAW_RATIFIED_DIR, BYLAW_CACHE_DIR]   # no MODEL_API_KEY
$ docker compose down
 Container agent-a789027e774655c41-bylaw-1 Removed
```

The offline airline audit (budget 2000, blind BFS) takes about 252 s in the container.

## To test

`docker compose build && docker compose up -d`, then `curl localhost:8000/api/domains`, open `http://localhost:8000/`, run an audit from the UI or with the POST above, and finish with `docker compose down`.

## Not verified

- A Muse audit (`use_llm=true`) in the container, because it needs the key.
- The VPS deploy, which waits for the user's go-ahead.
- An amd64 build. Only arm64 was built here. The base images are multi-arch.

## VPS notes (for later)

Run `git clone` and `docker compose up -d` in the checkout, so that `./reports` (the DM1 demo reports) is the mounted store. Put `MODEL_API_KEY` in `.env` next to `docker-compose.yml` on the server. The container runs as root so that bind-mounted directories are writable without a chown.
