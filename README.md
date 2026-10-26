# Bylaw

## Quickstart

Needs `git`, `make`, [uv](https://docs.astral.sh/uv/) and Node.js with npm (for `web/`).

```sh
git clone https://github.com/Martinhdeez/meta-hackathon.git
cd meta-hackathon
make setup                # clones tau2-bench at the pinned commit, runs uv sync and npm ci in web/
cp .env.example .env      # then set MODEL_API_KEY in .env
make check
```
