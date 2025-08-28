.PHONY: format format-diff ruff-check pyright-check ci

format:
	../../scripts/format.sh .

format-diff:
	../../scripts/format.sh --diff .

ruff-check:
	uv run ruff check .

pyright-check:
	uv run pyright

ci: format-diff ruff-check pyright-check
	@echo "Done"