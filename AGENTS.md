## Build & Run
- Package manager: `uv`
- Install deps: `uv sync --all-extras`
- Run the app: `uv run uvicorn ralf-spike-2.main:app`
- Source code: `src/`
- Tests: `tests/`
- Specs: `specs/` (branch-specific subdirectories, e.g. `specs/{branch}`)

## Validation

Run these after implementing to get immediate feedback:

- Tests: `uv run pytest`
- Typecheck: `uv run pyright`
- Lint: `uv run ruff check`

## Operational Notes
- Python 3.12, strict pyright, ruff already configured.

### Plan Conventions

- Plans are branch-specific: `.ralph/plans/IMPLEMENTATION_PLAN_{branch}.md`. Tasks use `[ ]` (incomplete) and `[x]` (complete).
- A task is complete when all its required tests exist and pass. Update status as part of each iteration.
