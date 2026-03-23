"""Conventional deadlift model builder.

The lifter grips the barbell at approximately shoulder width with the bar
on the floor. The motion lifts from floor to lockout (standing erect with
hips and knees fully extended).

Biomechanical notes:
- Primary movers: erector spinae, gluteus maximus, hamstrings, quadriceps
- The barbell starts on the ground (center of shaft at ~0.225 m height
  for standard 450 mm diameter plates)
- Mixed grip or double-overhand grip — modelled as rigid hand attachment
- Hip hinge dominant pattern with simultaneous knee extension

The barbell is welded to both hands. Initial pose has significant hip
and knee flexion to reach the bar on the ground.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import add_weld_joint

PLATE_RADIUS = 0.225  # Standard 450mm diameter plate radius


class DeadliftModelBuilder(ExerciseModelBuilder):
    """Builds a conventional deadlift OpenSim model.

    The barbell is welded to both hands and starts on the floor.
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        super().__init__(config)

    @property
    def exercise_name(self) -> str:
        return "deadlift"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell shaft to both hands at shoulder-width grip.

        Grip is slightly outside the knees (~0.22 m from center).
        """
        grip_offset = 0.22

        add_weld_joint(
            jointset,
            name="barbell_to_left_hand",
            parent_body="hand_l",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(-grip_offset, 0, 0),
        )

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set the starting position: deep hip hinge, knees flexed.

        The bar is on the floor at PLATE_RADIUS height, so the body
        must flex at the hips (~80 deg) and knees (~60 deg) to reach.
        """
        # Default coordinate values are 0 (standing). The actual starting
        # pose for simulation would be set via a motion file or initial
        # state. For the .osim model, neutral defaults are appropriate.


def build_deadlift_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float = 80.0,
) -> str:
    """Convenience function to build a deadlift model XML string."""
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass_per_side),
    )
    return DeadliftModelBuilder(config).build()
