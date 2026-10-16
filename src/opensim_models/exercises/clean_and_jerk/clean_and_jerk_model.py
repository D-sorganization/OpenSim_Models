"""Clean and jerk model builder.

The clean and jerk is a two-part lift:

**Clean** — bar from floor to front-rack (shoulders):
1. First pull — bar leaves the floor (similar to deadlift)
2. Transition / scoop — knees re-bend
3. Second pull — explosive triple extension
4. Turnover — elbows rotate forward, bar lands on front deltoids
5. Front squat catch — receive bar in front rack at bottom of squat
6. Recovery — stand from front squat

**Jerk** — bar from shoulders to overhead:
1. Dip — slight knee bend to load legs
2. Drive — explosive leg drive pushes bar upward
3. Split / push / squat jerk — lifter drops under bar
4. Recovery — bring feet together, stand with bar overhead

Biomechanical notes:
- Grip width: the standard's clean grip (``grip.width_m``)
- Front rack requires significant wrist/elbow flexibility
- Jerk phase requires rapid coordination of upper and lower body
- Primary movers: entire posterior chain + quadriceps + deltoids + triceps

The barbell is welded to both palm centres. The default state is the
standard's clean-and-jerk ``start`` via-pose (UpstreamDrift#11743).
"""

from __future__ import annotations

import logging

from opensim_models.exercises.spec_start import SpecLiftModelBuilder, spec_lift_config

logger = logging.getLogger(__name__)


class CleanAndJerkModelBuilder(SpecLiftModelBuilder):
    """Builds a clean-and-jerk OpenSim model.

    Uses the spec clean grip. The model supports both the clean
    (floor to shoulders) and jerk (shoulders to overhead) phases.
    """

    seat_feet_at_equilibrium = True  # #472, as MuJoCo_Models#447/#453

    @property
    def exercise_name(self) -> str:
        return "clean_and_jerk"

    @property
    def spec_exercise(self) -> str:
        return "clean_and_jerk"


def build_clean_and_jerk_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float | None = None,
) -> str:
    """Convenience function to build a clean and jerk model XML string.

    ``plate_mass_per_side=None`` is the spec load.
    """
    config = spec_lift_config("clean_and_jerk", body_mass, height, plate_mass_per_side)
    return CleanAndJerkModelBuilder(config).build()
