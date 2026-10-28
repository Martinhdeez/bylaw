# DP2 Deploy hardening (DP1 review advisories)

- `docker-compose.yml`: `bylaw` publishes no port any more. A new `caddy` service (`caddy:2.10.2-alpine`) is the only public entry, on 80, 443 and 443/udp, with the `caddy_data` and `caddy_config` volumes.
  - `BYLAW_BASIC_AUTH_USER` and `BYLAW_BASIC_AUTH_HASH` come from `.env` through compose interpolation, with `:?`, so compose refuses to start without them.
  - `BYLAW_DOMAIN` defaults to `:80` in compose. Caddy keeps an empty variable empty instead of using its own default, and an empty site address turns the block into a global options block, so Caddy failed to start (seen on the first run).
- `Caddyfile`: `{$BYLAW_DOMAIN::80}` site, `basic_auth` over every path, `reverse_proxy bylaw:8000` with `flush_interval -1` for SSE. With a domain, `caddy adapt` gives a `:443` server matched on that host (automatic HTTPS).
- `.dockerignore`: `.env` and `.env.*` replaced by `**/.env*`.
- `reports/.gitkeep`, `ratified/.gitkeep`. `git check-ignore` matches neither. The API reads `reports/<domain>.json`, `.cache/reports/<domain>-*.json` and `ratified/<domain>.json` by name, so `.gitkeep` is never read: `/api/reports/latest?domain=airline` 200, `?domain=retail` 404 (no report), `/api/ratified?domain=airline` 200.
- `.env.example`: the three variables, with the `caddy hash-password` command and the single-quote rule for the hash.
- `docs/deploy.md`: runbook for the VPS (Compose >= 2.24, clone, `.env`, DNS, ufw with only 22/80/443, start, check, update, backup and restore of `reports`, `ratified` and `.cache`).

## Proof (local Docker 29.5.3, Compose v5.1.4, arm64, 2026-10-27)

Local quirk, as in DP1: the daemon has no free address pool, because of leftover networks from other worktrees, which I left alone. I added an uncommitted override that gives the default network the subnet `10.231.7.0/24`, and ran under the project name `dp2proof` with a throwaway env file (user `tester`, password `dp2-local-test`).

```
$ docker compose ps
dp2proof-bylaw-1   bylaw:local           Up About a minute (healthy)   8000/tcp
dp2proof-caddy-1   caddy:2.10.2-alpine   Up 29 seconds                 0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp, 0.0.0.0:443->443/udp (+ [::])
no auth /                 -> HTTP 401
no auth /api/domains      -> HTTP 401
no auth POST /api/audits  -> HTTP 401
wrong password            -> HTTP 401
auth /                    -> HTTP 200 text/html; charset=utf-8
auth /api/domains         -> HTTP 200 ["airline","retail"]
POST /api/audits {"domain":"airline","use_llm":false,"budget":200,"amend":false} -> id 99edf807a984
curl -N .../events, each line stamped with its local arrival time (84 events):
18:58:01 data: {"phase": "compile", "message": "hand RuleSet bylaw/rulesets/airline.json, 27 rules", ...
18:58:03 data: {"phase": "search", "message": "1 tool calls executed", ...
18:58:30 data: {"phase": "search", "message": "118 tool calls executed", ...
18:58:57 data: {"phase": "verify", "message": "9 Class A holes, 0 contradictions and 2 ambiguities proven 5/5", ...
18:58:57 data: {"phase": "done", "message": "report stored as airline-99edf807a984.json", ...
LAN interface en0: 192.168.1.130
curl http://192.168.1.130:8000/api/domains -> HTTP 000, curl rc=7 (connection refused)
curl -u ... http://192.168.1.130/api/domains -> HTTP 200
docker port dp2proof-bylaw-1 -> (nothing)
```

The events arrive over 56 s, one every 0.5 to 1 s, so Caddy does not buffer the stream.

Cleanup: `docker compose down -v` removed the two containers, the two caddy volumes and the network. I deleted the test `.cache/` in the worktree and the pulled `caddy:2.10.2-alpine` image. The `bylaw:local` tag was rebuilt and kept.

## To test

Copy `.env.example` to `.env`, set the user and hash, then `docker compose up -d --build`. `curl localhost/` gives 401, `curl -u user:pass localhost/api/domains` gives the domains. Finish with `docker compose down`.

## Not verified

- Automatic HTTPS with a real domain. This Mac has no public DNS name. Only `caddy adapt` with `BYLAW_DOMAIN=bylaw.example.org` was checked.
- ufw on the VPS, and the VPS deploy itself, which waits for the user's go-ahead.
- The backup and restore commands in `docs/deploy.md`.

## Review (2026-10-27)

Approved. Reviewer reproduced on Docker 29.5.3, Compose v5.1.4, with an uncommitted subnet override and a throwaway env file: no published port on `bylaw` (`docker port` empty), 401 without or with wrong credentials on `/`, `/api/domains`, `POST /api/audits`; 200 with credentials on `/` (text/html) and `/api/domains`; offline airline audit streamed 83 SSE events through Caddy over 53 s, arriving in 54 distinct seconds; LAN `192.168.1.130:8000` refused (rc 7), LAN `:80` 401/200. An unquoted hash is mangled by compose (`$$2a$$14`), so the single-quote rule is needed. Image holds no env file of its own (only tau2's upstream `.env.example`).

Advisories for the VPS deploy, not blocking:
- `docs/deploy.md` step 5: `ufw allow OpenSSH` covers port 22 only; if sshd listens elsewhere, allow that port before `ufw enable`.
- `docs/deploy.md` restore: on Linux the container runs as root, so `.cache/reports` and `.cache/llm` are root-owned; extracting over them as a normal user fails. Restore into a fresh checkout, or with `sudo`.
- `docs/deploy.md` update: `docker image prune -f` removes every dangling image on the host, not only the old `bylaw` one.
