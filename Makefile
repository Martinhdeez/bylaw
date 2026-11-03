TAU2_REPO := https://github.com/sierra-research/tau2-bench.git
TAU2_COMMIT := 0c69df456a96aa76a1162591574dad9c427a34d7
TAU2_DIR := .context/tau2-bench

.PHONY: setup check tau2

setup:
	@if [ ! -f $(TAU2_DIR)/pyproject.toml ]; then \
		git init -q $(TAU2_DIR) && \
		git -C $(TAU2_DIR) fetch -q --depth 1 $(TAU2_REPO) $(TAU2_COMMIT) && \
		git -C $(TAU2_DIR) checkout -q FETCH_HEAD; \
	fi
	uv sync
	@if [ -f web/package.json ]; then cd web && npm ci; fi
	cd targets/cs_demo/ui && npm ci

tau2:
	@test -f $(TAU2_DIR)/pyproject.toml || { echo "$(TAU2_DIR) is missing. Run 'make setup' first."; exit 1; }

check: tau2
	uv run pytest -q
	@if [ -f web/package.json ]; then cd web && npm run build; fi
	cd targets/cs_demo/ui && npm ci --prefer-offline --no-audit --no-fund && NEXT_TELEMETRY_DISABLED=1 npm run build
