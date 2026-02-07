## Build & Run

- Package manager: `uv`
- Install deps: `uv sync --all-extras`
- Run the app: `DATABASE_URL=sqlite:///data/todos.db uv run uvicorn ralf_spike_2.main:app`
- Source code: `src/ralf_spike_2/`
- Tests: `tests/`
- Specs: `specs/`

## Validation

Run these after implementing to get immediate feedback:

- Tests: `uv run pytest`
- Typecheck: `uv run pyright`
- Lint: `uv run ruff check src tests`

## Operational Notes

- Python 3.12, strict pyright, ruff linting already configured in `pyproject.toml`.
- Project uses `hatchling` build backend with `src` layout (`src/ralf_spike_2/`).
- Test config: `testpaths = ["tests"]`, `pythonpath = ["src"]`.
- Use `DATABASE_URL=sqlite:///:memory:` for test fixtures.

### Codebase Patterns

- Type annotations are mandatory (pyright strict mode).
- Follow existing ruff rules — see `pyproject.toml [tool.ruff.lint]` for enabled rule sets.
