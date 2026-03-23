# Contributing to OpenSim Models

Thank you for your interest in contributing! This document outlines the
process and guidelines for contributing to this project.

## Getting Started

1. Fork the repository and clone your fork.
2. Create a virtual environment and install development dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
3. Create a feature branch from `main`:
   ```bash
   git checkout -b fix/issue-XXXX-description
   ```

## Development Workflow

### Running Tests

```bash
python3 -m pytest tests/ -v --tb=short
```

### Linting and Formatting

```bash
ruff check src scripts tests
ruff format src scripts tests
```

Both checks must pass before a PR will be merged.

### Type Checking

```bash
mypy src --config-file pyproject.toml
```

## Pull Request Guidelines

- Keep PRs focused on a single concern.
- Include tests for new functionality.
- All CI checks must pass before merge.
- Use descriptive commit messages explaining *why*, not just *what*.
- Reference related GitHub issues in the PR description.

## Code Style

- Follow PEP 8 (enforced by ruff).
- Use type annotations for all public function signatures.
- Use Design-by-Contract patterns: preconditions validate inputs,
  postconditions validate outputs.
- Keep functions small and single-purpose.
- No `TODO` or `FIXME` comments unless a tracked GitHub issue exists.

## Architecture Notes

- **Exercise builders** inherit from `ExerciseModelBuilder` (Template Method pattern).
- **Shared utilities** live in `src/opensim_models/shared/` and are reused across exercises.
- **Geometry/inertia** calculations are centralized in `geometry.py`.
- **XML generation** is handled by `xml_helpers.py` (single source of truth for OpenSim XML structure).

## Reporting Issues

Use GitHub Issues with a clear title and description. Include:
- Steps to reproduce (if a bug).
- Expected vs. actual behavior.
- Python version and OS.
