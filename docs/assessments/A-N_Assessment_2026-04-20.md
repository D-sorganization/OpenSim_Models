# A-N Assessment - OpenSim_Models - 2026-04-20

Run time: 2026-04-20T08:03:08.8387406Z UTC
Sync status: pull-blocked
Sync notes: ff-only pull failed: fatal: couldn't find remote ref codex/an-assessment-2026-04-14

Overall grade: C (75/100)

## Coverage Notes
- Reviewed tracked first-party files from git ls-files, excluding cache, build, vendor, virtualenv, temp, and generated output directories.
- Reviewed 127 tracked files, including 98 code files, 42 test files, 1 CI files, 2 config/build files, and 19 docs/onboarding files.
- This is a read-only static assessment of committed files. TDD history and confirmed Law of Demeter semantics require commit-history review and deeper call-graph analysis; this report distinguishes those limits from confirmed file evidence.

## Category Grades
### A. Architecture and Boundaries: B (82/100)
Assesses source organization and boundary clarity from tracked first-party layout.
- Evidence: `127 tracked first-party files`
- Evidence: `54 files under source-like directories`

### B. Build and Dependency Management: C (72/100)
Assesses committed build, dependency, and tool configuration.
- Evidence: `Dockerfile`
- Evidence: `pyproject.toml`

### C. Configuration and Environment Hygiene: C (78/100)
Checks whether runtime and developer configuration is explicit.
- Evidence: `Dockerfile`
- Evidence: `pyproject.toml`

### D. Contracts, Types, and Domain Modeling: B (82/100)
Design by Contract evidence includes validation, assertions, typed models, explicit raised errors, and invariants.
- Evidence: `rust_core/src/dynamics.rs`
- Evidence: `rust_core/src/interpolation.rs`
- Evidence: `rust_core/src/kinematics.rs`
- Evidence: `src/opensim_models/exercises/base.py`
- Evidence: `src/opensim_models/optimization/_types.py`
- Evidence: `src/opensim_models/optimization/exercise_objectives.py`
- Evidence: `src/opensim_models/optimization/trajectory_optimizer.py`
- Evidence: `src/opensim_models/shared/barbell/barbell_model.py`
- Evidence: `src/opensim_models/shared/body/_segment_data.py`
- Evidence: `src/opensim_models/shared/contracts/postconditions.py`

### E. Reliability and Error Handling: C (76/100)
Reliability is graded from test presence plus explicit validation/error-handling signals.
- Evidence: `tests/__init__.py`
- Evidence: `tests/integration/__init__.py`
- Evidence: `tests/integration/test_all_exercises_build.py`
- Evidence: `tests/integration/test_gait_integration.py`
- Evidence: `tests/integration/test_sit_to_stand_integration.py`
- Evidence: `rust_core/src/dynamics.rs`
- Evidence: `rust_core/src/interpolation.rs`
- Evidence: `rust_core/src/kinematics.rs`
- Evidence: `src/opensim_models/exercises/base.py`
- Evidence: `src/opensim_models/optimization/_types.py`

### F. Function, Module Size, and SRP: C (70/100)
Evaluates function size, script/module size, and single responsibility using static size signals.
- Evidence: `src/opensim_models/shared/parity/standard.py (coarse avg 89 lines/definition)`

### G. Testing and TDD Posture: B (82/100)
TDD history cannot be confirmed statically; grade reflects committed automated test posture.
- Evidence: `tests/__init__.py`
- Evidence: `tests/integration/__init__.py`
- Evidence: `tests/integration/test_all_exercises_build.py`
- Evidence: `tests/integration/test_gait_integration.py`
- Evidence: `tests/integration/test_sit_to_stand_integration.py`
- Evidence: `tests/parity/__init__.py`
- Evidence: `tests/parity/test_parity_compliance.py`
- Evidence: `tests/unit/__init__.py`
- Evidence: `tests/unit/exercises/__init__.py`
- Evidence: `tests/unit/exercises/bench_press/__init__.py`
- Evidence: `tests/unit/exercises/bench_press/test_bench_press_model.py`
- Evidence: `tests/unit/exercises/clean_and_jerk/__init__.py`

### H. CI/CD and Automation: C (78/100)
Checks for tracked CI/CD workflow files.
- Evidence: `.github/workflows/ci-standard.yml`

### I. Security and Secret Hygiene: B (82/100)
Secret scan is regex-based; findings require manual confirmation.
- Evidence: No direct tracked-file evidence found for this category.

### J. Documentation and Onboarding: B (82/100)
Checks docs, README, onboarding, and release documents.
- Evidence: `.github/PULL_REQUEST_TEMPLATE.md`
- Evidence: `AGENTS.md`
- Evidence: `CHANGELOG.md`
- Evidence: `CLAUDE.md`
- Evidence: `CODE_OF_CONDUCT.md`
- Evidence: `CONTRIBUTING.md`
- Evidence: `Dockerfile`
- Evidence: `LICENSE`
- Evidence: `README.md`
- Evidence: `SECURITY.md`
- Evidence: `SPEC.md`
- Evidence: `docs/assessments/A-N_Assessment_2026-04-02.md`

### K. Maintainability, DRY, and Duplication: B (80/100)
DRY is assessed through duplicate filename clusters and TODO/FIXME density as static heuristics.
- Evidence: No direct tracked-file evidence found for this category.

### L. API Surface and Law of Demeter: F (58/100)
Law of Demeter is approximated with deep member-chain hints; confirmed violations require semantic review.
- Evidence: `src/opensim_models/exercises/__init__.py`
- Evidence: `src/opensim_models/exercises/base.py`
- Evidence: `src/opensim_models/exercises/bench_press/__init__.py`
- Evidence: `src/opensim_models/exercises/bench_press/bench_press_model.py`
- Evidence: `src/opensim_models/exercises/clean_and_jerk/__init__.py`
- Evidence: `src/opensim_models/exercises/deadlift/__init__.py`
- Evidence: `src/opensim_models/exercises/gait/__init__.py`
- Evidence: `src/opensim_models/exercises/gait/gait_model.py`
- Evidence: `src/opensim_models/exercises/sit_to_stand/__init__.py`
- Evidence: `src/opensim_models/exercises/sit_to_stand/sit_to_stand_model.py`

### M. Observability and Operability: F (55/100)
Checks for logging, metrics, monitoring, and operational artifacts.
- Evidence: No direct tracked-file evidence found for this category.

### N. Governance, Licensing, and Release Hygiene: C (74/100)
Checks ownership, release, contribution, security, and license metadata.
- Evidence: `CHANGELOG.md`
- Evidence: `CONTRIBUTING.md`
- Evidence: `LICENSE`
- Evidence: `SECURITY.md`

## Explicit Engineering Practice Review
- TDD: Automated tests are present, but red-green-refactor history is not confirmable from static files.
- DRY: No repeated filename clusters met the static threshold.
- Design by Contract: Validation/contract signals were found in tracked code.
- Law of Demeter: Deep member-chain hints were found and should be semantically reviewed.
- Function size and SRP: Large modules or coarse long-definition signals were found.

## Key Risks
- Deep member-chain usage may indicate Law of Demeter pressure points.

## Prioritized Remediation Recommendations
1. Review deep member chains and introduce boundary methods where object graph traversal leaks across modules.

## Actionable Issue Candidates
### Review deep object traversal hotspots
- Severity: medium
- Problem: Deep member-chain hints found in: src/opensim_models/exercises/__init__.py; src/opensim_models/exercises/base.py; src/opensim_models/exercises/bench_press/__init__.py; src/opensim_models/exercises/bench_press/bench_press_model.py; src/opensim_models/exercises/clean_and_jerk/__init__.py; src/opensim_models/exercises/deadlift/__init__.py; src/opensim_models/exercises/gait/__init__.py; src/opensim_models/exercises/gait/gait_model.py
- Evidence: Category L found repeated chains with three or more member hops.
- Impact: Law of Demeter pressure can make APIs brittle and increase coupling.
- Proposed fix: Review hotspots and introduce boundary methods or DTOs where callers traverse object graphs.
- Acceptance criteria: Hotspots are documented, simplified, or justified; tests cover any API boundary changes.
- Expectations: Law of Demeter, SRP, maintainability

