# DP3 Deploy readiness for the 06 additions

Prepare only. No VPS, no registry push, no DNS change.

- `Dockerfile`: copies `targets/` (the vendored cs demo, VN1) into `/app`. The pinned `openai-agents==0.24.0` and `openai-chatkit==1.6.5` were already in `uv.lock`, so `uv sync --frozen` installs them.
- `reports/live/` needs no change: `reports/` is already bind-mounted (`docker-compose.yml`) and kept out of the build context (`.dockerignore`), as is `ratified/`. Recordings committed under `reports/live/` reach the server with `git pull`.
- No key is baked in: `.dockerignore` drops `**/.env*`, the image config sets no key, and the container starts healthy without `MODEL_API_KEY`.
- `docs/deploy.md`: new "06 additions" section and a pre-flight checklist for the real deploy.

To test: `docker compose build bylaw`, start `bylaw` alone with a published port, then curl `/`, `/api/domains`, `/api/reports/latest?domain=airline`, `/api/live`. On this machine it ran as image `bylaw:dp3`, published on `127.0.0.1:18093` with `network_mode: bridge`, because the docker address pools are exhausted here. The override was local only and is not committed.

`GET /api/live` answers 404 (JSON `{"detail":"Not Found"}`) until CS3 (#35) merges. After that it should answer `[]` until DM2 commits recordings.

Not covered: Caddy and basic auth (DP2 covered them, and Caddy is unchanged), a Muse audit or the `live` runner inside the container, and the image after CS2/CS3 merge.

## Smoke output

```
## dp3 smoke, 2026-10-28T20:59:01Z, image bylaw:dp3, container dp3-bylaw-1
container: Up 16 seconds (healthy) 127.0.0.1:18093->8000/tcp
GET / -> 200 text/html; charset=utf-8 1364B
GET /api/domains -> 200 application/json 20B
GET /api/reports/latest?domain=airline -> 200 application/json 583210B
GET /api/reports/latest?domain=retail -> 200 application/json 10450B
GET /api/bench?domain=airline -> 200 application/json 1780B
GET /api/live -> 404 application/json 22B
GET / title: <title>Bylaw</title>
GET /api/domains: ["airline","retail"]
GET /api/live first bytes: {"detail":"Not Found"}
## inside the container
MODEL_API_KEY set: False
env files in /app: []
openai-agents 0.24.0 | openai-chatkit 1.6.5
targets.cs_demo.airline.agents imported from /app/targets/cs_demo/airline/agents.py
reports/: ['.gitkeep', 'airline.bench.json', 'airline.json', 'retail.json']
## image config env names (no values): PATH LANG GPG_KEY(python base image signing key id, public) PYTHON_VERSION PYTHON_SHA256 TAU2_DATA_DIR BYLAW_REPORTS_DIR BYLAW_RATIFIED_DIR BYLAW_CACHE_DIR
```
