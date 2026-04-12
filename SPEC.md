# OpenSim_Models Specification

## 1. Identity

| Field | Value |
| --- | --- |
| Repository | `OpenSim_Models` |
| GitHub | `https://github.com/D-sorganization/OpenSim_Models` |
| Primary language | Python 3.10+ |
| Package name | `opensim_models` |
| Distribution name | `opensim-models` |
| Current version | `0.1.0` |

## 2. Purpose

OpenSim_Models provides a small library and CLI for generating OpenSim `.osim`
musculoskeletal models for classical barbell exercises. The maintained surface
is intentionally focused on model assembly, XML generation, and testable
geometry/contracts rather than on a live OpenSim runtime dependency.

## 3. Public Surface

| Surface | Location | Notes |
| --- | --- | --- |
| Package import | `src/opensim_models/__init__.py` | Exposes the package version only. |
| Module entrypoint | `python -m opensim_models` | Dispatches to the CLI in `__main__.py`. |
| Console script | `opensim-models` | Configured in `pyproject.toml`. |
| Exercise registry | `src/opensim_models/exercises/__init__.py` | Single source of truth for supported exercise builders. |
| Model builders | `src/opensim_models/exercises/*/*_model.py` | Return `.osim` XML strings for each exercise. |

The current supported exercise builders are:

- `bench_press`
- `clean_and_jerk`
- `deadlift`
- `gait`
- `sit_to_stand`
- `snatch`
- `squat`

## 4. Architecture

### Package layout

```text
src/opensim_models/
├── __init__.py
├── __main__.py
├── exercises/
│   ├── base.py
│   ├── constants.py
│   ├── bench_press/
│   ├── clean_and_jerk/
│   ├── deadlift/
│   ├── gait/
│   ├── sit_to_stand/
│   ├── snatch/
│   └── squat/
├── optimization/
├── shared/
│   ├── barbell/
│   ├── body/
│   ├── contracts/
│   ├── parity/
│   └── utils/
└── visualization/
```

### Core responsibilities

- `shared/body/` builds the canonical full-body musculoskeletal structure.
- `shared/barbell/` builds the shared Olympic barbell geometry.
- `shared/contracts/` holds precondition and postcondition helpers.
- `shared/utils/` contains XML, geometry, and contact helpers used by builders.
- `exercises/` composes shared components into exercise-specific models.
- `optimization/` holds trajectory/objective helpers for downstream use.
- `visualization/` contains plotting helpers for generated models and results.

## 5. CLI Contract

`src/opensim_models/__main__.py` accepts:

- a required `exercise` name from the exercise registry
- optional `--output/-o` path for the generated `.osim`
- optional `--mass`, `--height`, and `--plates` numeric inputs
- optional `--verbose` logging

The CLI validates basic numeric bounds before model construction and writes the
generated XML string to disk. Barbell exercises accept plate mass; `gait` and
`sit_to_stand` do not.

## 6. Data And Configuration

| Input | Source | Notes |
| --- | --- | --- |
| Body mass and height | CLI args or direct builder calls | Used to parameterize anthropometrics. |
| Plate mass per side | CLI args or direct builder calls | Ignored for non-barbell exercises. |
| OpenSim XML output | Builder return values | Builders return XML strings; the CLI writes files. |

The repository does not require an installed OpenSim runtime to validate the
XML structure. The test suite checks generated XML directly.

## 7. Testing And CI

| Area | Current contract |
| --- | --- |
| Test runner | `pytest` |
| Coverage target | `>= 80%` |
| Linting | `ruff` |
| Type checking | `mypy` |
| Test organization | `tests/unit`, `tests/integration`, `tests/parity` |

Key test expectations:

- all exercise builders must produce valid `OpenSimDocument` XML
- the model registry must stay aligned with the supported CLI exercises
- parity constants must remain consistent with the fleet-wide biomechanical standard
- integration tests should cover the end-to-end build path for each exercise

## 8. Generated Artifacts

The repo is source-first. Generated `.osim` files are produced on demand by the
CLI or by direct builder calls and are not treated as maintained source files.

## 9. Change Log

| Date | Version | Notes |
| --- | --- | --- |
| 2026-04-11 | 1.0.2 | Expanded `tests/unit/test_trajectory_optimizer.py` and `tests/unit/test_limb_builders.py` with additional happy-path, edge-case, and DbC coverage for every public entry point (issue #130). |
| 2026-04-09 | 1.0.1 | Replaced handwritten XML indentation with `xml.etree.ElementTree.indent`, standardized deadlift feasibility warnings on repo logging, and removed redundant builder constructors while preserving constructor coverage in tests. |
| 2026-04-05 | 1.0.0 | Initial root specification for the maintained OpenSim_Models package and CLI surface. |
