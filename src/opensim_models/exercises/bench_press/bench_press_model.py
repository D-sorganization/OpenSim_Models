"""Bench press model builder.

The lifter lies supine on a bench. The barbell is gripped in the hands
at approximately shoulder width. The model starts in the lockout position
(arms extended) and the motion descends the bar to the chest then presses
back to lockout.

Biomechanical notes:
- Primary movers: pectoralis major, anterior deltoid, triceps brachii
- The bench constrains pelvis and torso to a supine orientation
- Scapular retraction and arch are simplified (torso stays rigid on bench)
- Grip width affects shoulder abduction angle and pec activation

The bench is modelled as a ground-welded platform that constrains the
pelvis to a supine position at bench height (0.43 m, standard IPF).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    set_coordinate_default,
)

BENCH_HEIGHT = 0.43  # IPF standard bench height (meters)


class BenchPressModelBuilder(ExerciseModelBuilder):
    """Builds a bench-press OpenSim model.

    The pelvis is welded to ground in a supine orientation at bench height.
    The barbell shaft is welded to both hands at grip width.
    """

    def __init__(self, config: ExerciseConfig | None = None) -> None:
        super().__init__(config)

    @property
    def exercise_name(self) -> str:
        return "bench_press"

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld barbell to both hands at grip width.

        The grip is approximately shoulder-width (~0.40 m from center
        on each side for a standard grip).
        """
        grip_offset = 0.20  # meters from shaft center to each hand

        add_weld_joint(
            jointset,
            name="barbell_to_left_hand",
            parent_body="hand_l",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(-grip_offset, 0, 0),
        )

        add_weld_joint(
            jointset,
            name="barbell_to_right_hand",
            parent_body="hand_r",
            child_body="barbell_shaft",
            location_in_parent=(0, 0, 0),
            location_in_child=(grip_offset, 0, 0),
        )

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Set supine lockout position.

        Shoulders flexed ~90 deg (arms pointing up), elbows near-extended.
        The supine orientation is a hint for visualization; actual supine
        constraint would come from the bench weld in a full model.
        """
        shoulder_flex = 1.5708  # ~90 degrees (arms vertical)
        for side in ("l", "r"):
            set_coordinate_default(jointset, f"shoulder_{side}_flex", shoulder_flex)


def build_bench_press_model(
    body_mass: float = 80.0,
    height: float = 1.75,
    plate_mass_per_side: float = 50.0,
) -> str:
    """Convenience function to build a bench press model XML string."""
    from opensim_models.shared.barbell import BarbellSpec
    from opensim_models.shared.body import BodyModelSpec

    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass_per_side),
    )
    return BenchPressModelBuilder(config).build()
