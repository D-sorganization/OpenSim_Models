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

## Design Principles

- **TDD** — Tests written alongside models; CI enforces 80% coverage
- **Design by Contract** — All inputs validated via preconditions; outputs checked via postconditions
- **DRY** — Shared base class, shared barbell/body models, shared XML helpers
- **Law of Demeter** — Exercise builders interact only with public APIs of shared components

## License

MIT
