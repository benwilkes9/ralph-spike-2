# ralf-spike-2



## Development

```bash
# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint and format
uv run ruff check src tests
uv run ruff format src tests

# Type check
uv run pyright

# Install pre-commit hooks
uv run pre-commit install
```
