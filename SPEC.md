# OpenSim_Models Specification

## 1. Identity

| Field             | Value                                               |
| ----------------- | --------------------------------------------------- |
| Repository        | `OpenSim_Models`                                    |
| GitHub            | `https://github.com/D-sorganization/OpenSim_Models` |
| Primary language  | Python 3.10+                                        |
| Package name      | `opensim_models`                                    |
| Distribution name | `opensim-models`                                    |
| Current version   | `1.0.33`                                            |

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

| Area              | Current contract                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Test runner       | `pytest`                                                                                                                                                     |
| Coverage target   | `>= 80%`                                                                                                                                                     |
| Linting           | `ruff`                                                                                                                                                       |
| Type checking     | `mypy`                                                                                                                                                       |
| Test organization | `tests/unit`, `tests/integration`, `tests/parity`                                                                                                            |
| Runner policy     | Lightweight public CI defaults to GitHub-hosted Linux and returns to `d-sorg-fleet` with `CI_RUNNER_MODE=local`; private repositories and Rust remain local. |

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

## Engine Parity Contract

Cross-engine parameters come from the fleet parity standard vendored at
`src/opensim_models/shared/parity/_canonical/` (`biomech_parity_standard.json`,
`conformance.py`, `assemble.py`, `MANIFEST.json`). The canonical source is
`Repository_Management/shared_scripts/model_parity/`; vendored files are never
edited here and `tests/parity/` verifies their hashes against `MANIFEST.json`.

- `shared/parity/standard.py` and the body segment table are computed from the
  bundle; no constants are duplicated.
- `shared/parity/fingerprint.py` loads every exercise's generated .osim model in
  the real opensim engine and reports a `model-fingerprint/v1`
  (`python -m opensim_models.shared.parity.fingerprint --all --out DIR`).
- `tests/parity/test_engine_conformance.py` runs in default CI with the engine
  installed and fails on any divergence from the standard that is not listed,
  with an issue reference, in `shared/parity/parity_divergences.json`. Ledger
  entries that no longer diverge fail as stale, so the ledger only shrinks.
- `model_pack.yaml` declares honest `capabilities` levels (`none`, `partial`,
  `full`); `full` requires a public API and a real-engine test as evidence.

## 9. Change Log

Rows are keyed by pull request, not by a serial spec version: `| YYYY-MM-DD | #<pr> | summary |`. Add exactly one row for your own pull request and do not renumber anybody else's; the `Spec Version` field in section 1 is bumped at release time by `scripts/bump_spec_version.py`, never by an individual pull request. See [Repository_Management#1520](https://github.com/D-sorganization/Repository_Management/issues/1520).

| Date       | PR    | Changes                                                                                                                                                                                                                                                                                                  |
| ---------- | ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-10-05 | #400 | wire collate-changes workflow and check_spec_freshness into spec-check |
| 2026-10-05 | #399 | chore(changes): vendor RM-5 change-fragment tooling and test suite (ref Repository_Management#2019) |
| 2026-10-05 | #385 | Re-vendor the fleet parity bundle (Repository_Management#2012/#2014/#2015); the `root_joint` ledger entry is scoped to `bench_press` (welded pelvis) so it cannot hide a missing free root in another exercise. Conformance tests reconcile per exercise and check staleness with `reconcile_all`. |
| 2026-10-05 | #382 | Free-root models now start resting on the ground: `pelvis_ty` default is derived from the generated skeleton and initial pose (`shared/body/ground_placement.py`) so the lowest foot-sphere surface touches y = 0 (sit_to_stand: pelvis rests on the seat); the ground_pelvis FreeJoint frames coincide. |
| 2026-10-05 | #379 | Generated .osim now loads in OpenSim 4.6 (set <objects> wrappers, six-axis CustomJoints, SmoothSphereHalfSpaceForce contact, right-hand grip as WeldConstraint, Y-up foot spheres); real-engine parity conformance against the fleet standard. |
| 2026-09-29 | #371 | Inlined `float_str` scalar formatting in `_joints.py` to eliminate function call overhead during XML coordinate generation. |
| 2026-09-19 | #388 | Optimized `require_unit_vector` to calculate squared magnitude instead of `math.hypot()` to avoid square root overhead. |
| 2026-09-17 | n/a | Optimized `preconditions.py` fast-paths by reordering type checks, prioritizing success-case short circuits, and replacing `math.hypot()` with squared magnitude comparisons. (spec 1.0.30) |
| 2026-09-10 | #1606 | Adopted Mermaid C4 architecture-map contract in `docs/architecture/C4.md` with C4Context, C4Container, and Feature Map, validated by `scripts/architecture_map_contract.py` and enforced in CI (issue #1606). (spec 1.0.29) |
| 2026-08-31 | n/a | Replaced manual Python for loop with ElementTree's `.find()` method in bench press model to avoid Python iteration overhead and speed up XML generation. (spec 1.0.28) |
| 2026-08-30 | n/a | Added fast-path for 6-vectors in `require_shape` by unrolling the shape checking for `expected == (6,)` lists/tuples. (spec 1.0.27) |
| 2026-08-26 | n/a | Added tuple equality short-circuiting fast-paths (`type(val) is tuple and val == (0.0, 0.0, 0.0)`) across XML element generation helpers for joints, bodies, and contact geometries to bypass `vec3_str` call overhead without triggering NumPy array truth-value ambiguity. (spec 1.0.26) |
| 2026-08-02 | n/a | Refactored `add_pin_joint` to use `_add_joint_frames` fast-paths (spec 1.0.24) |
| 2026-08-01 | n/a | Optimized XML tuple validation strings in `_joints.py` by applying an inline tuple equality check (`== (0.0, 0.0, 0.0)`) before falling back to `vec3_str`, thereby bypassing the function call overhead for common zero-vectors entirely. (spec 1.0.23) |
| 2026-07-24 | n/a | Moved `ensure_coordinates_within_bounds` validation before XML serialization to create a fail-fast execution order and removed redundant `findall` XML parsing overhead in `bench_press_model.py` by directly capturing the returned `ET.Element`. (spec 1.0.22) |
| 2026-07-08 | n/a | Optimized `_joints.py` and `_bodies.py` by replacing multiple f-strings with old-style `%` formatting for OpenSim `range` and `inertia` XML elements, reducing model generation string overhead. (spec 1.0.20) |
| 2026-06-14 | n/a | Cast Matplotlib `rc_context` style dictionaries at the call boundary so CI type checking accepts the intentionally constrained visualization defaults without changing plotting behavior. (spec 1.0.19) |
| 2026-08-03 | n/a | Added a zero-polling reversible hosted fast lane for lightweight public CI while keeping Rust work on the local fleet. (spec 1.0.20) |
| 2026-06-14 | n/a | Removed undeclared pytest-asyncio configuration from the strict pytest contract so CI jobs do not fail before collection. (spec 1.0.18) |
| 2026-06-14 | n/a | Batched XML coordinate updates in `set_coordinate_defaults`, reducing redundant $O(N^2)$ traversal overhead during initial pose setup. (spec 1.0.17) |
| 2026-06-02 | n/a | Optimized precondition check hot-paths (`require_shape`, `require_finite`, `require_unit_vector`) by utilizing `arr.item()` for fast scalar retrieval from numpy arrays and replacing negative exclusion lists with positive exact type-checking inclusions. (spec 1.0.16) |
| 2026-05-31 | n/a | Added fast-paths for diagonal inertia matrices in XML generation to avoid unnecessary string formatting overhead for zero off-diagonal elements. (spec 1.0.15) |
| 2026-05-28 | n/a | Replaced `isinstance` with exact type checks (`type(x) is float`) in the scalar fast-path of `require_finite` to avoid MRO overhead, maintaining `isinstance` as a fallback. (spec 1.0.14) |
| 2026-05-25 | n/a | Optimized `require_finite` validation function in `preconditions.py` using `.all()` and unrolled `math.isfinite` checks, improving performance by up to 7x for hot-path spatial vectors. (spec 1.0.13) |
| 2026-05-23 | n/a | Replaced inline f-string formatting with a `float_str` helper for scalar XML attributes, speeding up common 0.0 values by ~10x via literal return strings. (spec 1.0.12) |
| 2026-05-22 | n/a | Optimized `build` method in `base.py` to bypass redundant XML string parsing, reducing model generation time by ~20%. (spec 1.0.11) |
| 2026-05-20 | n/a | Optimized validation checking for 3D vectors in `preconditions.py` (`require_shape`) using explicit unrolled loops and `type(...) is ...` to reduce execution time overhead. (spec 1.0.10) |
| 2026-05-11 | n/a | Replaced `isinstance` with exact type checking `type(x) is list or type(x) is tuple` in `require_unit_vector` to eliminate MRO resolution overhead in standard validation paths. (spec 1.0.9) |
| 2026-05-01 | n/a | Added fast-paths for strictly zero vectors in `vec3_str` and `vec6_str` OpenSim XML generation utilities to return pre-formatted zero literals, bypassing interpolation overhead for common default poses. (spec 1.0.8) |
| 2026-04-30 | #245 | Swapped f-strings for `%` formatting in `vec3_str`/`vec6_str` to reduce XML formatting overhead; pinned `ndarray` to `0.16` in `rust_core/Cargo.toml` to resolve version mismatch with `numpy 0.22` (PR #245). (spec 1.0.7) |
| 2026-04-29 | n/a | Replaced slow Python exponentiation `**2` with fast multiplication `x * x` in core geometry constructors, speeding up execution by ~40-55%. (spec 1.0.6) |
| 2026-04-27 | #232 | Added `.env.example` template; fixed ruff I001 import sorting in `__main__.py` and `_formatting.py` (PR #232). (spec 1.0.5) |
| 2026-04-22 | #176 | Declared `pyyaml` in the dev extra so YAML-parsing workflow regression tests run in clean CI installs (issue #176). (spec 1.0.4) |
| 2026-04-11 | #127 | Split `rust_core/src/lib.rs` into focused submodules (`dynamics`, `kinematics`, `interpolation`) to stay under the monolith threshold; public PyO3 API and behaviour unchanged (issue #127). (spec 1.0.3) |
| 2026-04-11 | #130 | Expanded `tests/unit/test_trajectory_optimizer.py` and `tests/unit/test_limb_builders.py` with additional happy-path, edge-case, and DbC coverage for every public entry point (issue #130). (spec 1.0.2) |
| 2026-04-09 | n/a | Replaced handwritten XML indentation with `xml.etree.ElementTree.indent`, standardized deadlift feasibility warnings on repo logging, and removed redundant builder constructors while preserving constructor coverage in tests. (spec 1.0.1) |
| 2026-04-05 | n/a | Initial root specification for the maintained OpenSim_Models package and CLI surface. (spec 1.0.0) |
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

<!-- Updated: 2026-06-14T09:35:00 -->

- 2026-09-14: Downgraded non-existent workflow action versions to @v4/@v5 across workflows (#348).
- 2026-09-14: Removed invalid pip cache from redundant closer workflows (#350).
