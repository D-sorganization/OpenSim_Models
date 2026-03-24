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

import math
import warnings
import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    set_coordinate_default,
)

PLATE_RADIUS = 0.225  # Standard 450mm diameter plate radius
_DEADLIFT_GRIP_HALF_WIDTH = 0.22  # metres from shaft center to each hand

# Named angle constants for use in feasibility check
DEADLIFT_INITIAL_HIP_ANGLE: float = 1.3963    # ~80 degrees hip flexion
DEADLIFT_INITIAL_KNEE_ANGLE: float = -1.0472  # ~60 degrees knee flexion (negative)
DEADLIFT_INITIAL_LUMBAR_ANGLE: float = 0.5236  # ~30 degrees lumbar flexion


class DeadliftModelBuilder(ExerciseModelBuilder):
    """Builds a conventional deadlift OpenSim model.

    The barbell is welded to both hands and starts on the floor.
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        super().__init__(config)

    @property
    def exercise_name(self) -> str:
        return "deadlift"

    def _check_pose_feasibility(self) -> None:
        """Warn if the initial pose likely places hands far from barbell height."""
        h = self.config.body_spec.height
        # Approx Winter (2009) fractions
        shank = h * 0.246
        thigh = h * 0.245
        torso = h * 0.288
        upper_arm = h * 0.186
        forearm = h * 0.146

        knee_z = shank * math.cos(abs(DEADLIFT_INITIAL_KNEE_ANGLE))
        hip_z = knee_z + thigh * math.cos(abs(DEADLIFT_INITIAL_HIP_ANGLE))
        torso_top_z = hip_z + torso * math.cos(abs(DEADLIFT_INITIAL_LUMBAR_ANGLE))
        hand_z = torso_top_z - upper_arm - forearm

        if abs(hand_z - PLATE_RADIUS) > 0.15:
            warnings.warn(
                f"Deadlift initial pose: estimated hand height {hand_z:.3f} m differs from "
                f"bar height {PLATE_RADIUS:.3f} m by {abs(hand_z - PLATE_RADIUS):.3f} m. "
                f"Consider adjusting DEADLIFT_INITIAL_* angles.",
                stacklevel=3,
            )

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell shaft to both hands at shoulder-width grip.

        Grip is slightly outside the knees (~0.22 m from center).
        """
        add_weld_joint(
            jointset,
            name="barbell_to_left_hand",
            parent_body="hand_l",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(-_DEADLIFT_GRIP_HALF_WIDTH, 0, 0),
        )

        add_weld_joint(
            jointset,
            name="barbell_to_right_hand",
            parent_body="hand_r",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(_DEADLIFT_GRIP_HALF_WIDTH, 0, 0),
        )

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set the starting position: deep hip hinge, knees flexed.

        The bar is on the floor at PLATE_RADIUS height, so the body
        must flex at the hips (~80 deg) and knees (~60 deg) to reach.
        Runs a feasibility check and emits a warning if hands are far
        from bar height.
        """
        for side in ("l", "r"):
            set_coordinate_default(jointset, f"hip_{side}_flex", DEADLIFT_INITIAL_HIP_ANGLE)
            set_coordinate_default(jointset, f"knee_{side}_flex", DEADLIFT_INITIAL_KNEE_ANGLE)
        set_coordinate_default(jointset, "lumbar_flex", DEADLIFT_INITIAL_LUMBAR_ANGLE)

        self._check_pose_feasibility()


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
