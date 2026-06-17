# OpenSim_Models Specification

## 1. Identity

| Field             | Value                                               |
| ----------------- | --------------------------------------------------- |
| Repository        | `OpenSim_Models`                                    |
| GitHub            | `https://github.com/D-sorganization/OpenSim_Models` |
| Primary language  | Python 3.10+                                        |
| Package name      | `opensim_models`                                    |
| Distribution name | `opensim-models`                                    |
| Current version   | `1.0.20`                                            |

## 2. Purpose

OpenSim_Models provides a small library and CLI for generating OpenSim `.osim`
musculoskeletal models for classical barbell exercises. The maintained surface
is intentionally focused on model assembly, XML generation, and testable
geometry/contracts rather than on a live OpenSim runtime dependency.

## 3. Public Surface

| Surface           | Location                                    | Notes                                                   |
| ----------------- | ------------------------------------------- | ------------------------------------------------------- |
| Package import    | `src/opensim_models/__init__.py`            | Exposes the package version only.                       |
| Module entrypoint | `python -m opensim_models`                  | Dispatches to the CLI in `__main__.py`.                 |
| Console script    | `opensim-models`                            | Configured in `pyproject.toml`.                         |
| Exercise registry | `src/opensim_models/exercises/__init__.py`  | Single source of truth for supported exercise builders. |
| Model builders    | `src/opensim_models/exercises/*/*_model.py` | Return `.osim` XML strings for each exercise.           |

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

| Input                | Source                           | Notes                                              |
| -------------------- | -------------------------------- | -------------------------------------------------- |
| Body mass and height | CLI args or direct builder calls | Used to parameterize anthropometrics.              |
| Plate mass per side  | CLI args or direct builder calls | Ignored for non-barbell exercises.                 |
| OpenSim XML output   | Builder return values            | Builders return XML strings; the CLI writes files. |

The repository does not require an installed OpenSim runtime to validate the
XML structure. The test suite checks generated XML directly.

## 7. Testing And CI

| Area              | Current contract                                                                                                                                                          |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Test runner       | `pytest`                                                                                                                                                                  |
| Coverage target   | `>= 80%`                                                                                                                                                                  |
| Linting           | `ruff`                                                                                                                                                                    |
| Type checking     | `mypy`                                                                                                                                                                    |
| Test organization | `tests/unit`, `tests/integration`, `tests/parity`                                                                                                                         |
| Runner policy     | `.github/workflows/local-only-runner-guard.yml` runs `scripts/check_local_only_workflows.py` on `d-sorg-fleet` and fails if any workflow routes to GitHub-hosted runners. |

Key test expectations:

- all exercise builders must produce valid `OpenSimDocument` XML
- the model registry must stay aligned with the supported CLI exercises
- parity constants must remain consistent with the fleet-wide biomechanical standard
- integration tests should cover the end-to-end build path for each exercise
- pytest configuration must not reference plugin-specific options unless the
  matching plugin is declared in the development dependency set

## 8. Generated Artifacts

The repo is source-first. Generated `.osim` files are produced on demand by the
CLI or by direct builder calls and are not treated as maintained source files.

## 9. Change Log

| Date       | Version | Notes                                                                                                                                                                                                                                                        |
| ---------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-06-17 | 1.0.20  | Added unrolled `require_finite` fast paths for flat built-in 3- and 6-element list/tuple vectors while preserving finite-value validation and fallback behavior for nested or array-like inputs.                                                             |
| 2026-06-14 | 1.0.19  | Cast Matplotlib `rc_context` style dictionaries at the call boundary so CI type checking accepts the intentionally constrained visualization defaults without changing plotting behavior.                                                                    |
| 2026-06-14 | 1.0.18  | Removed undeclared pytest-asyncio configuration from the strict pytest contract so CI jobs do not fail before collection.                                                                                                                                    |
| 2026-06-14 | 1.0.17  | Batched XML coordinate updates in `set_coordinate_defaults`, reducing redundant $O(N^2)$ traversal overhead during initial pose setup.                                                                                                                       |
| 2026-06-02 | 1.0.16  | Optimized precondition check hot-paths (`require_shape`, `require_finite`, `require_unit_vector`) by utilizing `arr.item()` for fast scalar retrieval from numpy arrays and replacing negative exclusion lists with positive exact type-checking inclusions. |
| 2026-05-31 | 1.0.15  | Added fast-paths for diagonal inertia matrices in XML generation to avoid unnecessary string formatting overhead for zero off-diagonal elements.                                                                                                             |
| 2026-05-28 | 1.0.14  | Replaced `isinstance` with exact type checks (`type(x) is float`) in the scalar fast-path of `require_finite` to avoid MRO overhead, maintaining `isinstance` as a fallback.                                                                                 |
| 2026-05-25 | 1.0.13  | Optimized `require_finite` validation function in `preconditions.py` using `.all()` and unrolled `math.isfinite` checks, improving performance by up to 7x for hot-path spatial vectors.                                                                     |
| 2026-05-23 | 1.0.12  | Replaced inline f-string formatting with a `float_str` helper for scalar XML attributes, speeding up common 0.0 values by ~10x via literal return strings.                                                                                                   |
| 2026-05-22 | 1.0.11  | Optimized `build` method in `base.py` to bypass redundant XML string parsing, reducing model generation time by ~20%.                                                                                                                                        |
| 2026-05-20 | 1.0.10  | Optimized validation checking for 3D vectors in `preconditions.py` (`require_shape`) using explicit unrolled loops and `type(...) is ...` to reduce execution time overhead.                                                                                 |
| 2026-05-11 | 1.0.9   | Replaced `isinstance` with exact type checking `type(x) is list or type(x) is tuple` in `require_unit_vector` to eliminate MRO resolution overhead in standard validation paths.                                                                             |
| 2026-05-01 | 1.0.8   | Added fast-paths for strictly zero vectors in `vec3_str` and `vec6_str` OpenSim XML generation utilities to return pre-formatted zero literals, bypassing interpolation overhead for common default poses.                                                   |
| 2026-04-30 | 1.0.7   | Swapped f-strings for `%` formatting in `vec3_str`/`vec6_str` to reduce XML formatting overhead; pinned `ndarray` to `0.16` in `rust_core/Cargo.toml` to resolve version mismatch with `numpy 0.22` (PR #245).                                               |
| 2026-04-29 | 1.0.6   | Replaced slow Python exponentiation `**2` with fast multiplication `x * x` in core geometry constructors, speeding up execution by ~40-55%.                                                                                                                  |
| 2026-04-27 | 1.0.5   | Added `.env.example` template; fixed ruff I001 import sorting in `__main__.py` and `_formatting.py` (PR #232).                                                                                                                                               |
| 2026-04-22 | 1.0.4   | Declared `pyyaml` in the dev extra so YAML-parsing workflow regression tests run in clean CI installs (issue #176).                                                                                                                                          |
| 2026-04-11 | 1.0.3   | Split `rust_core/src/lib.rs` into focused submodules (`dynamics`, `kinematics`, `interpolation`) to stay under the monolith threshold; public PyO3 API and behaviour unchanged (issue #127).                                                                 |
| 2026-04-11 | 1.0.2   | Expanded `tests/unit/test_trajectory_optimizer.py` and `tests/unit/test_limb_builders.py` with additional happy-path, edge-case, and DbC coverage for every public entry point (issue #130).                                                                 |
| 2026-04-09 | 1.0.1   | Replaced handwritten XML indentation with `xml.etree.ElementTree.indent`, standardized deadlift feasibility warnings on repo logging, and removed redundant builder constructors while preserving constructor coverage in tests.                             |
| 2026-04-05 | 1.0.0   | Initial root specification for the maintained OpenSim_Models package and CLI surface.                                                                                                                                                                        |

## 10. Internationalisation

### Current Scope (Explicit)

OpenSim_Models is **English-only**. All user-facing strings — log messages,
exception messages, and CLI output — are in English. This is a deliberate
choice, not an accidental omission.

**Rationale:**

- The primary audience is biomechanics researchers who read English as the
  standard scientific lingua franca.
- The package surface is a model-generation library, not a consumer-facing
  application; translation is out of scope for the current release cycle.
- Keeping strings centralised in a single module (`_messages.py`) means
  i18n can be added later (e.g. via `gettext` or `babel`) without touching
  logic files.

### String Management

All user-visible strings are sourced from
`src/opensim_models/_messages.py`. Hardcoded strings in other modules
are considered a regression and should be refactored into `_messages.py`.

### Future Milestone

If the CLI or documentation expands to non-researcher audiences,
consider:

1. Adding `babel` or `gettext` as an optional dependency.
2. Extracting `_messages.py` into `.po` / `.mo` files per locale.
3. Documenting the locale-aware formatting decision in `CONTRIBUTING.md`.

Until then, `_messages.py` remains a simple Python constants module.

<!-- Updated: 2026-06-17T05:30:00 -->
