# OpenSim Models

OpenSim musculoskeletal models for classical barbell exercises.

## Exercises

| Exercise       | Module                              | Description                                    |
| -------------- | ----------------------------------- | ---------------------------------------------- |
| Back Squat     | `exercises.squat`                   | High-bar back squat with barbell on trapezius   |
| Bench Press    | `exercises.bench_press`             | Supine press with barbell gripped at chest      |
| Deadlift       | `exercises.deadlift`                | Conventional deadlift from floor to lockout     |
| Snatch         | `exercises.snatch`                  | Wide-grip floor-to-overhead in one motion       |
| Clean and Jerk | `exercises.clean_and_jerk`          | Floor to shoulders (clean) + overhead (jerk)    |

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

## Architecture

- **`shared/`** — Reusable components (DRY)
  - `barbell/` — Olympic barbell model (IWF/IPF spec)
  - `body/` — Full-body musculoskeletal model (Winter 2009 anthropometrics)
  - `contracts/` — Design-by-Contract preconditions and postconditions
  - `utils/` — XML generation helpers and geometry/inertia calculations
- **`exercises/`** — Exercise-specific model builders
  - Each exercise inherits from `ExerciseModelBuilder` (base class)
  - Customizes barbell attachment and initial pose

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

## License

MIT
