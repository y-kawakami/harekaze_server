# Python Package Management Rules

## Use uv for Package Management

This project uses **uv** as the package manager with `pyproject.toml` for dependency specification.

### Adding Dependencies

```bash
# Add a new package
uv add <package-name>

# Add with version constraint
uv add <package-name>>=1.0.0

# Add as dev dependency
uv add --dev <package-name>
```

### Prohibited Patterns

```bash
# DO NOT use pip directly
pip install <package>  # Bad

# DO NOT edit pyproject.toml manually for adding packages
# (uv add handles this automatically)
```

### Syncing Dependencies

```bash
# Install all dependencies from pyproject.toml
uv sync

# Update lock file
uv lock
```

### Running Commands

```bash
# Run Python scripts
uv run python script.py

# Run pytest
uv run pytest

# Or use the virtual environment directly
python -m pytest
```

### Project Structure

- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Lock file for reproducible installs
- `.venv/` - Virtual environment (managed by uv)
