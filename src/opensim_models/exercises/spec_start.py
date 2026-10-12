"""Barbell lifts that start at their standard ``start`` via-pose.

UpstreamDrift#11743 (LIFT-3): every barbell lift's generated model holds the
vendored standard's ``start`` via-pose by default -- all joint coordinates,
the pelvis root and the bar -- instead of pack-local start-pose literals.
The hands meet the bar at the palm centre (``grip_point``) at the spec grip
width, and each grip weld's frames are the exact start-pose relationship
between hand and bar, so ``initSystem()`` has nothing to reassemble.

Design by Contract:
    - Preconditions: a configured grip must equal the spec grip (the start
      pose is solved for it); violations raise ValueError.
    - Postconditions: each palm centre lies within ``GRIP_CLOSURE_TOL_M`` of
      its spec point on the bar; otherwise ValueError (the spec pose and the
      pack geometry disagree).
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from abc import abstractmethod
from dataclasses import dataclass

import numpy as np

from opensim_models.exercises.base import ExerciseConfig, ExerciseModelBuilder
from opensim_models.shared.barbell import BarbellSpec
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.parity import via_poses
from opensim_models.shared.utils.constraint_helpers import add_weld_constraint
from opensim_models.shared.utils.xml_helpers import (
    add_weld_joint,
    set_coordinate_defaults,
)

Vec3 = tuple[float, float, float]
START = "start"
GRIP_CLOSURE_TOL_M = 0.005  # Repository_Management#2060 condition 1


def _vec3(values: object) -> Vec3:
    x, y, z = (float(v) for v in np.asarray(values, dtype=float))
    return x, y, z


def spec_lift_config(
    exercise: str,
    body_mass: float,
    height: float,
    plate_mass_per_side: float | None,
) -> ExerciseConfig:
    """Config of a spec lift; ``plate_mass_per_side=None`` is the spec load."""
    plates = (
        via_poses.plates_per_side_kg(exercise)
        if plate_mass_per_side is None
        else plate_mass_per_side
    )
    return ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=body_mass, height=height),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=plates),
    )


@dataclass(frozen=True)
class GripWeld:
    """One hand's bar weld: a frame on the hand and the shaft point it holds."""

    hand_location: Vec3
    hand_orientation: Vec3
    shaft_location: Vec3


def attach_barbell_to_hands(
    jointset: ET.Element, model: ET.Element, left: GripWeld, right: GripWeld
) -> None:
    """Weld the barbell shaft to both hands.

    The left hand is the shaft's parent joint; the right hand is a
    ``WeldConstraint`` (one parent per body). Shaft frames carry no
    orientation: the hand frames already hold the shaft's axes.
    """
    add_weld_joint(
        jointset,
        name="barbell_to_left_hand",
        parent_body="hand_l",
        child_body="barbell_shaft",
        location_in_parent=left.hand_location,
        location_in_child=left.shaft_location,
        orientation_in_parent=left.hand_orientation,
    )
    add_weld_constraint(
        model,
        name="barbell_to_right_hand",
        body_1="hand_r",
        body_2="barbell_shaft",
        location_in_body_1=right.hand_location,
        location_in_body_2=right.shaft_location,
        orientation_in_body_1=right.hand_orientation,
    )


def spec_grip_welds(exercise: str, height_m: float) -> tuple[GripWeld, GripWeld]:
    """(left, right) grip welds holding the bar at the spec start pose.

    Raises:
        ValueError: a palm centre is more than ``GRIP_CLOSURE_TOL_M`` from its
            spec point on the bar (``bar_position_m`` +/- grip width / 2).
    """
    bar = via_poses.bar_position(exercise, START, height_m)
    palm = via_poses.palm_offset(height_m)
    half = via_poses.grip_half_width(exercise, height_m)
    welds = []
    # The bar axis is canonical +Y (left), i.e. OpenSim -Z.
    for side, sign in (("l", -1.0), ("r", 1.0)):
        origin, rot = via_poses.segment_frame(exercise, START, f"hand_{side}", height_m)
        offset = origin + rot @ palm - bar
        gap = math.dist(offset, (0.0, 0.0, sign * half))
        if gap > GRIP_CLOSURE_TOL_M:
            raise ValueError(
                f"{exercise}: spec start pose puts the {side} palm {gap:.4f} m "
                "off its grip point on the bar"
            )
        welds.append(
            GripWeld(
                hand_location=_vec3(palm),
                hand_orientation=via_poses.body_xyz_angles(rot.T),
                shaft_location=_vec3(offset),
            )
        )
    return welds[0], welds[1]


class SpecLiftModelBuilder(ExerciseModelBuilder):
    """A barbell lift whose default state is its spec ``start`` via-pose."""

    @property
    @abstractmethod
    def spec_exercise(self) -> str:
        """Exercise id in the parity standard (``squat``, ``deadlift`` ...)."""

    @property
    def height(self) -> float:
        """Lifter height in metres (LoD: avoids self.body_spec.height)."""
        return self.body_spec.height

    def set_initial_pose(self, jointset: ET.Element) -> None:
        """Every human coordinate at the spec start via-pose (unlisted = 0)."""
        set_coordinate_defaults(
            jointset, via_poses.coordinates(self.spec_exercise, START)
        )

    def _initial_root_coordinates(self, model: ET.Element) -> dict[str, float]:
        """The pelvis FreeJoint at the spec start root position and orientation."""
        return via_poses.root_coordinates(self.spec_exercise, START, self.height)

    def grip_welds(self) -> tuple[GripWeld, GripWeld]:
        """Spec grip welds; a configured grip must equal the spec grip.

        Raises:
            ValueError: ``config.grip_offset`` is set and differs from the spec
                half grip width (the start pose cannot close on another grip).
        """
        half = via_poses.grip_half_width(self.spec_exercise, self.height)
        requested = self.grip_offset
        if requested is not None and not math.isclose(requested, half, abs_tol=1e-9):
            raise ValueError(
                f"{self.spec_exercise}: grip_offset {requested} m differs from the "
                f"spec grip half width {half:.4f} m the start pose is solved for"
            )
        return spec_grip_welds(self.spec_exercise, self.height)

    def attach_barbell(
        self,
        jointset: ET.Element,
        body_bodies: dict[str, ET.Element],
        barbell_bodies: dict[str, ET.Element],
    ) -> None:
        """Weld the bar to both palms at the spec grip (hand-held lifts)."""
        attach_barbell_to_hands(jointset, self._model_el, *self.grip_welds())

    def weld_bar_to_segment(self, jointset: ET.Element, segment: str) -> None:
        """Weld the bar to *segment* where the spec start pose places it."""
        bar = via_poses.bar_position(self.spec_exercise, START, self.height)
        location, orientation = via_poses.point_in_segment(
            self.spec_exercise, START, segment, bar, self.height
        )
        add_weld_joint(
            jointset,
            name=f"barbell_to_{segment}",
            parent_body=segment,
            child_body="barbell_shaft",
            location_in_parent=_vec3(location),
            orientation_in_parent=orientation,
        )
