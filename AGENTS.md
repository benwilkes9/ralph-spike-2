## Build & Run

- Package manager: `uv`
- Install deps: `uv sync --all-extras`
- Run the app: `uv run uvicorn ralf_spike_2.app:app`
- Source code: `src/ralf_spike_2/`
- Tests: `tests/`
- Specs: `specs/`

## Validation

Run these after implementing to get immediate feedback:

- Tests: `uv run pytest`
- Typecheck: `uv run pyright`
- Lint: `uv run ruff check src tests`

## Operational Notes

- Python 3.12, strict pyright, ruff already configured in `pyproject.toml`.
- Project uses `hatchling` build backend with `src/ralf_spike_2` layout.
- Test config: `testpaths = ["tests"]`, `pythonpath = ["src"]`.
- Use `DATABASE_URL=sqlite:///:memory:` for test fixtures.

### Plan Conventions

- Tasks in `IMPLEMENTATION_PLAN.md` use `[ ]` (incomplete) and `[x]` (complete).
- A task is complete when all its required tests exist and pass. Update status as part of each iteration.

### Codebase Patterns

- Type annotations are mandatory (strict pyright).
- Follow existing ruff rules — see `pyproject.toml` for enabled rule sets.
