# Deploy runbook

Bylaw runs on one Linux server with Docker Compose. Two containers:

- `bylaw`: the API and the web UI on port 8000, reachable only on the compose network. The API has no auth of its own.
- `caddy` (`caddy:2.10.2-alpine`): the only public entry, on 80 and 443. It asks for HTTP basic auth on every path, then proxies to `bylaw:8000`. With `BYLAW_DOMAIN` set it gets a Let's Encrypt certificate and redirects HTTP to HTTPS; without it, it serves plain HTTP on :80.

Run every command below in the checkout directory on the server.

## Requirements

- Docker Engine and **Docker Compose 2.24 or later** (`docker compose version`). Older Compose rejects `env_file: required: false`.
- About 2 GB of disk for the image, plus the stores.

## First install

1. Clone the repository:

   ```sh
   git clone https://github.com/Martinhdeez/meta-hackathon.git bylaw
   cd bylaw
   mkdir -p .cache   # so Docker does not create it owned by root
   ```

   `reports/` and `ratified/` come from the repository (each holds a `.gitkeep`).

2. Make a password hash:

   ```sh
   docker run --rm caddy:2.10.2-alpine caddy hash-password --plaintext '<password>'
   ```

3. Create the env file from the template and fill it in:

   ```sh
   cp .env.example .env
   chmod 600 .env
   ```

   | Variable | Value |
   |---|---|
   | `MODEL_API_KEY` | the Meta Model API key. Optional: offline audits run without it. |
   | `BYLAW_BASIC_AUTH_USER` | the login name |
   | `BYLAW_BASIC_AUTH_HASH` | the hash from step 2, **in single quotes** (it contains `$`) |
   | `BYLAW_DOMAIN` | the domain, e.g. `bylaw.example.org`. Empty: plain HTTP on :80. |

   Compose refuses to start if the user or the hash is missing.

4. DNS: create an `A` record (and an `AAAA` record if the server has IPv6) for `BYLAW_DOMAIN` that points at the server. Wait until `dig +short <domain>` returns the server's address. Port 80 must be reachable from the internet for the certificate challenge.

5. Firewall: open only SSH, 80 and 443. With ufw:

   ```sh
   sudo ufw default deny incoming
   sudo ufw allow OpenSSH
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 443/udp   # HTTP/3
   sudo ufw enable
   ```

   Docker publishes container ports past ufw, so ufw alone does not protect a published port. That is why only `caddy` publishes ports. Do not add a `ports:` entry to `bylaw`.

6. Start:

   ```sh
   docker compose up -d --build
   docker compose ps          # bylaw "healthy", caddy "Up"
   docker compose logs caddy  # look for "certificate obtained successfully"
   ```

7. Check from another machine:

   ```sh
   curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/                       # 401
   curl -s -u '<user>:<password>' https://<domain>/api/domains                      # ["airline","retail"]
   curl -s -m 5 http://<server-ip>:8000/ ; echo $?                                  # 7 or 28: closed
   ```

## Update

```sh
git pull
docker compose up -d --build
docker image prune -f   # removes the previous, now untagged bylaw image
```

Audits that are running when `bylaw` restarts are lost; their finished reports are kept in `.cache/reports`.

To change the password, put a new hash in `.env` and run `docker compose up -d caddy`.

## Backup

The state lives in three bind-mounted directories:

| Directory | Contents |
|---|---|
| `reports/` | the committed demo reports and bench |
| `ratified/` | ratified amendments (`<domain>.json`). Not in git: back it up. |
| `.cache/` | reports of audits run through the API (`.cache/reports`) and the Muse response cache (`.cache/llm`, which saves budget on a re-run) |

Take a backup (the stores are plain JSON files, so a copy while running is fine):

```sh
tar czf ~/bylaw-backup-$(date +%F).tgz reports ratified .cache
```

Copy it off the server, e.g. `scp server:bylaw-backup-*.tgz .`. The `.env` file is not in the backup; keep the key and the password in a password manager.

Restore into a checkout:

```sh
docker compose down
tar xzf bylaw-backup-<date>.tgz
docker compose up -d
curl -s -u '<user>:<password>' "https://<domain>/api/ratified?domain=airline"   # the amendments are back
```

Caddy's certificates are in the `caddy_data` volume. They do not need a backup: Caddy gets new ones on start. `docker compose down -v` deletes that volume; repeated deletions can hit the Let's Encrypt rate limit.
