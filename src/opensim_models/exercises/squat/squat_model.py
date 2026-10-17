"""Back squat model builder.

The barbell rests across the upper back and is rigidly welded to the torso
where the standard's squat ``start`` via-pose places it (UpstreamDrift#11743).
The default state is that via-pose: standing at the unrack position with the
hands on the bar, feet flat at the spec stance.

Biomechanical notes:
- Primary movers: quadriceps, gluteus maximus, hamstrings, erector spinae
- The model captures sagittal-plane kinematics (flexion/extension)
- Barbell path should remain roughly over mid-foot
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.exercises.spec_start import SpecLiftModelBuilder, spec_lift_config

logger = logging.getLogger(__name__)


class SquatModelBuilder(SpecLiftModelBuilder):
    """Builds a back-squat OpenSim model at the spec ``start`` via-pose.

    The hands rest on the bar at the spec grip but are not welded: the torso
    carries the bar, so the bar has one parent.
    """

    seat_feet_at_equilibrium = True  # #472, as MuJoCo_Models#447/#453

    @property
    def exercise_name(self) -> str:
        return "back_squat"

    @property
    def spec_exercise(self) -> str:
        return "squat"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld the barbell shaft to the torso at the spec start bar position.

        Precondition: 'torso' exists in body_bodies.
        Precondition: 'barbell_shaft' exists in barbell_bodies.
        """
        self.weld_bar_to_segment(jointset, "torso")


def build_squat_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float | None = None,
) -> str:
    """Convenience function to build a squat model XML string.

    Default: 80 kg person, 1.75 m tall, the spec load (``None``: 20 kg bar +
    the standard's plates per side).
    """
    config = spec_lift_config("squat", body_mass, height, plate_mass_per_side)
    return SquatModelBuilder(config).build()
