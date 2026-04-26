# Criterion A: Project Organization

**Weight:** 5% | **Score:** 7.0/10 | **Grade:** C

## Evidence

- `src/opensim_models/` package with subpackages: `exercises/`, `shared/`, `optimization/`, `visualization/`
- 48 Python source files, 42 test files
- `pyproject.toml` present with hatchling build backend
- `.pre-commit-config.yaml` present with gitleaks, ruff, custom hooks
- Each exercise has dedicated module with `__init__.py`
- Test structure mirrors source: `tests/unit/exercises/`, `tests/unit/shared/`, etc.
- `conftest.py` at repo root

## Positive Findings

- Clear package hierarchy following Python conventions
- Source and test directory structures are symmetrical
- Build system properly configured in pyproject.toml

## Negative Findings

### P0-A001: File exceeds 300-line guideline
- `src/opensim_models/shared/body/body_model.py`: 272 lines (close to 300 limit)
- `src/opensim_models/shared/barbell/barbell_model.py`: 271 lines
- `src/opensim_models/shared/utils/xml_helpers.py`: 321 lines (exceeds limit)

### P2-A002: .coverage file tracked in repository
- `.coverage` SQLite file present at repo root (line 1 of evidence)
- Should be in `.gitignore` only

### P2-A003: Stale root files in .gitignore
- `.gitignore` lists `fix_mypy.py`, `mypy2.txt`, `os_issues.json`, `.ci_trigger.py` as stale
- These are debug artifacts that should not accumulate

## Justification

Good structural organization with clear separation of concerns. Deducted 3 points for files approaching/exceeding the 300-line guideline documented in AGENTS.md and for tracked artifacts that should be ignored.
