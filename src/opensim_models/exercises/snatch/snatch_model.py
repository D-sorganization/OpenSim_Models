"""Snatch model builder.

The snatch is a single continuous motion that lifts the barbell from the
floor to overhead in one movement. The lifter uses a wide (snatch) grip,
pulls the bar explosively, then drops under it into an overhead squat.

Phases:
1. First pull — bar leaves the floor (deadlift-like, wide grip)
2. Transition / scoop — knees re-bend, torso becomes more vertical
3. Second pull — explosive triple extension (ankle, knee, hip)
4. Turnover — lifter pulls under the bar, rotating arms overhead
5. Catch — overhead squat position (deep squat, arms locked overhead)
6. Recovery — stand up from overhead squat to full extension

Biomechanical notes:
- Grip width: ~1.5x shoulder width (approx 0.55-0.65 m from center)
- Primary movers: entire posterior chain, deltoids, trapezius
- Requires extreme shoulder mobility for overhead position
- Bar path is close to the body (S-curve trajectory)

The barbell is welded to both hands with a wide grip offset.
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
    _SNATCH_GRIP_HALF_WIDTH,
)
from opensim_models.shared.utils.xml_helpers import set_coordinate_default

logger = logging.getLogger(__name__)


class SnatchModelBuilder(ExerciseModelBuilder):
    """Builds a snatch OpenSim model with wide grip."""

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        super().__init__(config)

    @property
    def exercise_name(self) -> str:
        return "snatch"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell to both hands with wide (snatch) grip.

        Snatch grip is approximately 0.55-0.60 m from shaft center
        on each side (~1.5x shoulder width).
        """
        attach_barbell_to_hands(jointset, _SNATCH_GRIP_HALF_WIDTH)

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set starting position: bar on floor, wide grip, deep hip hinge.

        Wide snatch grip requires slight shoulder abduction.
        """
        set_floor_pull_initial_pose(jointset)
        shoulder_abduct = -0.3491  # ~-20° abduction for wide grip
        for side in ("l", "r"):
            set_coordinate_default(jointset, f"shoulder_{side}_adduct", shoulder_abduct)
            set_coordinate_default(jointset, f"shoulder_{side}_rotate", 0.0)


def build_snatch_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float = 40.0,
) -> str:
    """Convenience function to build a snatch model XML string.

    Default: 80 kg person, 100 kg total barbell (20 kg bar + 2 × 40 kg plates).
    """
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass_per_side),
    )
    return SnatchModelBuilder(config).build()
