"""Conventional deadlift model builder.

The lifter grips the barbell with the bar on the floor. The motion lifts from
floor to lockout (standing erect with hips and knees fully extended).

The default state is the standard's deadlift ``start`` via-pose
(UpstreamDrift#11743): the plates rest on the floor (bar centre at the plate
radius), the palms hold the bar at the spec grip width and the feet stand
flat at the spec stance.

Biomechanical notes:
- Primary movers: erector spinae, gluteus maximus, hamstrings, quadriceps
- Hook grip -- modelled as a rigid palm-centre attachment
- Hip hinge dominant pattern with simultaneous knee extension
"""

from __future__ import annotations

import logging

from opensim_models.exercises.spec_start import SpecLiftModelBuilder, spec_lift_config
from opensim_models.shared.parity.standard import STANDARD

logger = logging.getLogger(__name__)

# Bar centre height with the plates on the floor (standard plate diameter / 2).
PLATE_RADIUS: float = (
    float(STANDARD["exercises"]["deadlift"]["load"]["plate_diameter_m"]) / 2.0
)


class DeadliftModelBuilder(SpecLiftModelBuilder):
    """Builds a conventional deadlift OpenSim model.

    The barbell is welded to both palms and starts on the floor.
    """

    seat_feet_at_equilibrium = True  # #472, as MuJoCo_Models#447/#453

    @property
    def exercise_name(self) -> str:
        return "deadlift"

    @property
    def spec_exercise(self) -> str:
        return "deadlift"


def build_deadlift_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float | None = None,
) -> str:
    """Convenience function to build a deadlift model XML string.

    ``plate_mass_per_side=None`` is the spec load.
    """
    config = spec_lift_config("deadlift", body_mass, height, plate_mass_per_side)
    return DeadliftModelBuilder(config).build()
