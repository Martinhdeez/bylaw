check:
	uv run pytest -q
	@if [ -f web/package.json ]; then cd web && npm run build; fi
