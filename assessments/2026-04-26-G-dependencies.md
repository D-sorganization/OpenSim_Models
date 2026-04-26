# Criterion G: Dependencies

**Weight:** 8% | **Score:** 7.0/10 | **Grade:** C

## Evidence

- `pyproject.toml` dependencies: numpy>=1.26.4,<3.0.0, matplotlib>=3.7.0
- Optional deps: opensim>=4.5, pytest>=9.0.3, ruff>=0.15.10, mypy>=1.20.1, hypothesis>=6.0.0
- Build backend: hatchling
- Rust dependencies: pyo3 0.22, numpy 0.22, ndarray 0.16, rayon 1.10
- Dependabot configured: `.github/dependabot.yml`

## Positive Findings

- Minimal runtime dependencies (only numpy, matplotlib)
- Optional OpenSim dependency for runtime use
- Dependabot for automated dependency updates
- Version pinning for reproducibility

## Negative Findings

### P1-G001: numpy upper bound may be overly restrictive
- `numpy>=1.26.4,<3.0.0` — numpy 2.x is stable, upper bound prevents adoption

### P1-G002: Rust dependencies not locked
- No `Cargo.lock` committed in rust_core/
- PyO3/numpy bindings may break with patch updates

## Justification

Clean dependency tree with good separation of runtime/dev dependencies. Upper bounds and missing lockfile are the main concerns.
