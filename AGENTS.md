# AGENTS.md — Operational Notes

## How to run the application

```bash
uv run uvicorn ralf_spike_2.app:app --reload
```

## How to run tests

```bash
uv run pytest tests/ -v
```

## How to install dependencies

```bash
uv sync --all-extras
```

## Linting & Type Checking

```bash
uv run ruff check src/ tests/
uv run pyright src/ tests/
```

## Validation Steps Before Commit

1. `uv run pytest tests/ -v` — all tests pass
2. `uv run ruff check src/ tests/` — no lint errors
3. `uv run pyright src/ tests/` — no type errors
