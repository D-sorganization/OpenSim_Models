# Criterion N: API/Interface Design

**Weight:** 4% | **Score:** 7.0/10 | **Grade:** C

## Evidence

- Public API: `build_squat_model()`, `build_bench_press_model()`, etc.
- CLI: `opensim-models <exercise> [--output] [--mass] [--height] [--plates]`
- `__init__.py` exports `__version__` only
- Exercise builders dict: `EXERCISE_BUILDERS` in exercises/__init__.py
- Consistent function signatures: `(body_mass, height, plate_mass_per_side)`

## Positive Findings

- Simple, consistent builder API
- CLI mirrors programmatic API
- Type hints on CLI arguments

## Negative Findings

### P2-N001: Limited package exports
- `__init__.py` only exports `__version__`
- Users must import from submodules directly

## Justification

Clean API design but limited top-level package convenience exports.
