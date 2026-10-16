# OpenSim Models

OpenSim musculoskeletal models for classical barbell exercises.

## Exercises

| Exercise       | Module                     | Description                                   |
| -------------- | -------------------------- | --------------------------------------------- |
| Back Squat     | `exercises.squat`          | High-bar back squat with barbell on trapezius |
| Bench Press    | `exercises.bench_press`    | Supine press with barbell gripped at chest    |
| Deadlift       | `exercises.deadlift`       | Conventional deadlift from floor to lockout   |
| Snatch         | `exercises.snatch`         | Wide-grip floor-to-overhead in one motion     |
| Clean and Jerk | `exercises.clean_and_jerk` | Floor to shoulders (clean) + overhead (jerk)  |

## Quick Start

```bash
pip install -e ".[dev]"
python3 -m pytest
```

### Generate a model

```python
from opensim_models.exercises.squat.squat_model import build_squat_model

xml = build_squat_model(body_mass=80, height=1.75, plate_mass_per_side=60)
with open("squat.osim", "w") as f:
    f.write(xml)
```

### Headless rollout recording (#471)

`opensim_models.tools.record_rollout` records a forward-simulation rollout
without any GUI or Simbody visualizer. It writes the coordinate trajectory to
an OpenSim `.sto` file (`TimeSeriesTable` + `STOFileAdapter`, radians and
metres, loadable in the OpenSim GUI) and renders a matplotlib (Agg) sagittal
stick-figure animation from body-frame origins evaluated at each state. The
animation is MP4 when `ffmpeg` is available and GIF otherwise (an `.mp4`
request falls back to `.gif`; see `RolloutRecording.format`). The API mirrors
Pinocchio's `record_rollout`:

```python
from opensim_models.tools import record_rollout, run_forward_simulation

rec = record_rollout(
    "squat",
    lambda m: run_forward_simulation(m, duration=0.5),
    "squat.mp4",
    fps=30,
)
print(rec.path, rec.states_path, rec.frame_count, rec.format)
```

The stick figure is a kinematic rendering; it does not qualify the dynamics.

### Optional segmental lumbar chain (#464)

By default the trunk has one 3-DOF `lumbar` joint. Passing a coupling law in
`ExerciseConfig(lumbar_chain=...)` (or `lumbar_chain=` and `constraintset=` to
`create_full_body`) replaces it with five CustomJoints (`lumbar_L5_S1` ..
`lumbar_L1_L2`, caudal first) and twelve `CoordinateCouplerConstraint`s:

```python
from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.deadlift.deadlift_model import DeadliftModelBuilder
from opensim_models.shared.body.lumbar_coupling_data import xu2022_young_lumbar_law

xml = DeadliftModelBuilder(ExerciseConfig(lumbar_chain=xu2022_young_lumbar_law())).build()
```

Each motion's five shares (caudal first) are positive and sum to 1, so
`lumbar_flex`, `lumbar_lateral` and `lumbar_rotate` stay the total-motion
drivers with their original ranges. The law's id, version, source and DOI are
written to the model's `<publications>` property. The default model is
byte-identical (pinned SHA-256 per builder in
`tests/unit/shared/test_lumbar_chain_cited.py`).

- **Cited law:** `xu2022_young_lumbar_law()` uses the per-level in vivo
  rotation ranges of Xu et al. 2022, _Front Surg_ 9:1002133,
  doi:10.3389/fsurg.2022.1002133 (Table 1, young group, n = 14). Each level's
  share is its fraction of the summed range; that proportionality is a
  modelling assumption, not a published result.
- **Single source:** the cited per-level tables live only in
  `src/opensim_models/shared/body/lumbar_coupling_laws.json`;
  `load_lumbar_coupling_laws()` validates the file and builds every law from
  it, and a test fails if any Python module carries the numbers itself.
- **Limits:** each level's range is its share of the driver range, so the
  level limits are the cited per-level ranges scaled by one factor per motion.
- **Mass:** the four link bodies are carved from the torso (same mass centre,
  mass-proportional inertia), so the torso plus links keep the lumped torso's
  mass, mass centre and inertia in the neutral pose.
- Custom laws: `LumbarCouplingLaw(...)` with explicit `ratios`, or
  `LumbarCouplingLaw.from_level_rom(...)` from measured per-level ranges.
  `uniform_lumbar_law()` is an equal split, labelled as not published.
- Levels are co-located with no neutral lordosis, and there is no cross-axis
  coupling.

## Architecture

See [docs/architecture/C4.md](docs/architecture/C4.md) for the authoritative Mermaid C4 architecture map and feature-to-component traceability matrix.

- **`shared/`** — Reusable components (DRY)
  - `barbell/` — Olympic barbell model (IWF/IPF spec)
  - `body/` — Full-body musculoskeletal model (Winter 2009 anthropometrics)
  - `contracts/` — Design-by-Contract preconditions and postconditions
  - `utils/` — XML generation helpers and geometry/inertia calculations
- **`exercises/`** — Exercise-specific model builders
  - Each exercise inherits from `ExerciseModelBuilder` (base class)
  - Customizes barbell attachment and initial pose
  - The five barbell lifts inherit from `SpecLiftModelBuilder`
    (`exercises/spec_start.py`): every generated lift starts at the vendored
    parity standard's `start` via-pose -- joint coordinates, pelvis root, bar
    position, palm-centre grip at the standard grip width, feet flat at the
    standard stance -- with the standard load by default
    (`plate_mass_per_side=None`). `shared/parity/via_poses.py` converts the
    standard's canonical Z-up pose frame to OpenSim's Y-up frame.

## Testing

Agent-specific test commands for CI and local development:

```bash
# Run all unit tests (fast, no OpenSim required)
python3 -m pytest tests/unit/ -m unit -v

# Run integration tests (requires OpenSim package)
python3 -m pytest tests/integration/ -m integration -v

# Run parity/compliance tests across all exercises
python3 -m pytest tests/parity/ -v

# Run hypothesis property-based tests
python3 -m pytest tests/unit/test_hypothesis.py -v

# Run benchmark tests
python3 -m pytest tests/unit/test_benchmarks.py -v

# Run edge-case tests
python3 -m pytest tests/unit/test_edge_cases.py -v

# Run slow tests
python3 -m pytest tests/ -m slow -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html --cov-fail-under=80

# Run without parallel execution (for debugging)
python3 -m pytest tests/ -p no:xdist -v
```

## Design Principles

- **TDD** — Tests written alongside models; CI enforces 80% coverage
- **Design by Contract** — All inputs validated via preconditions; outputs checked via postconditions
- **DRY** — Shared base class, shared barbell/body models, shared XML helpers
- **Law of Demeter** — Exercise builders interact only with public APIs of shared components

## Used by UpstreamDrift

This package exposes a `model_pack/v1` manifest (`model_pack.yaml`) and a
`biomech.model_pack` entry point so that
[UpstreamDrift](https://github.com/D-sorganization/UpstreamDrift) can
discover and load OpenSim models without hard-coding paths. See umbrella
issue [UpstreamDrift#5179](https://github.com/D-sorganization/UpstreamDrift/issues/5179).
The OpenSim dashboard tracked in
[UpstreamDrift#5181](https://github.com/D-sorganization/UpstreamDrift/issues/5181)
depends on this integration.

Public API (under `opensim_models.model_pack`):

- `manifest()` — parsed `model_pack.yaml` as a dict.
- `resolve()` — absolute path to the exercises directory.
- `list_exercises()` — list of declared exercise IDs.

Launcher contract:

```bash
opensim-models --list-exercises
python -m opensim_models --exercise gait --export /tmp/gait.osim
```

## License

MIT
