# Bylaw

## Quickstart

Needs `git`, `make` and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Martinhdeez/meta-hackathon.git
cd meta-hackathon
make setup                # clones tau2-bench at the pinned commit, runs uv sync
cp .env.example .env      # then set MODEL_API_KEY in .env
make check
```
