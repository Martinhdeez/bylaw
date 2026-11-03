# DP1 Deploy on the VPS (Coolify/Traefik)

- `docker-compose.vps.yml`: `bylaw-api` (uvicorn, console + API) and `bylaw-ui` (Next.js demo UI), both on the external `coolify` network with Traefik labels, `pull_policy: never`, no published ports. `BYLAW_READONLY=1`, `BYLAW_LIVE_TOKEN_CAP=300000`, `BYLAW_LIVE` overridable. Key from `/etc/bylaw/bylaw.env` (root, 600).
- `targets/cs_demo/ui/Dockerfile` + `.dockerignore`: production build, `next start` on 3000, `BYLAW_API_URL=http://bylaw-api:8000`.
- `docs/deploy.md`: VPS section (URLs, secret, install, update, stop, rollback).

To test: `curl -sI https://bylaw.martinhdeez.com/` 200; `/api/live/status` shows enabled, cap 300000, readonly; `POST /api/holes/<key>/ratify?domain=airline` 403; a D1 replay loads; `https://console-bylaw.martinhdeez.com/` loads. Evidence: `.scratch/after/dp1/` (local, gitignored).
