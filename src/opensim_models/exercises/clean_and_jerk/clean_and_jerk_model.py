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
- Grip width: shoulder width or slightly outside (~0.25-0.30 m from center)
- Front rack requires significant wrist/elbow flexibility
- Jerk phase requires rapid coordination of upper and lower body
- Primary movers: entire posterior chain + quadriceps + deltoids + triceps

The barbell is welded to both hands at clean grip width.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.exercises.base import (
    ExerciseConfig,
    ExerciseModelBuilder,
    attach_barbell_to_hands,
    set_floor_pull_initial_pose,
)
from opensim_models.exercises.constants import (
    _CLEAN_GRIP_HALF_WIDTH,
)
from opensim_models.shared.body import shoulder_adduct_for_grip
from opensim_models.shared.utils.xml_helpers import set_coordinate_defaults

logger = logging.getLogger(__name__)


class CleanAndJerkModelBuilder(ExerciseModelBuilder):
    """Builds a clean-and-jerk OpenSim model.

    Uses shoulder-width grip. The model supports both the clean
    (floor to shoulders) and jerk (shoulders to overhead) phases.
    """

    @property
    def exercise_name(self) -> str:
        return "clean_and_jerk"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell to both hands at clean grip width.

        Clean grip: approximately shoulder width, ~0.25 m from shaft center.
        The shoulders are adducted (see ``set_initial_pose``) so the hands
        actually reach that width at the neutral pose (#394); the shaft is
        attached at the resulting feasible width, not the raw request.
        """
        _, feasible_grip = shoulder_adduct_for_grip(
            self.body_spec, _CLEAN_GRIP_HALF_WIDTH
        )
        attach_barbell_to_hands(jointset, feasible_grip, self._model_el)

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set starting position: bar on floor, clean grip, hip hinge.

        The shoulders are adducted so the hands reach the clean grip width;
        an equal, opposite wrist deviation (same mirrored axis) keeps the
        hands, and so the bar, level (#394).
        """
        set_floor_pull_initial_pose(jointset)

        shoulder_adduct, _ = shoulder_adduct_for_grip(
            self.body_spec, _CLEAN_GRIP_HALF_WIDTH
        )
        defaults = {}
        for side in ("l", "r"):
            defaults[f"shoulder_{side}_adduct"] = shoulder_adduct
            defaults[f"wrist_{side}_deviation"] = -shoulder_adduct
        set_coordinate_defaults(jointset, defaults)


def build_clean_and_jerk_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float = 50.0,
) -> str:
    """Convenience function to build a clean-and-jerk model XML string.

    Default: 80 kg person, 120 kg total barbell.
    """
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass_per_side),
    )
    return CleanAndJerkModelBuilder(config).build()
