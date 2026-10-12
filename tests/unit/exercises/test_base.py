"""Tests for the spec-lift grip welds in ``exercises.spec_start``."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.spec_start import (
    GRIP_CLOSURE_TOL_M,
    GripWeld,
    attach_barbell_to_hands,
    spec_grip_welds,
    spec_lift_config,
)
from opensim_models.shared.parity import via_poses

GRIP_LIFTS = ("deadlift", "bench_press", "snatch", "clean_and_jerk")


def _frame(root: ET.Element, name: str) -> tuple[str | None, str | None]:
    frame = root.find(f".//PhysicalOffsetFrame[@name='{name}']")
    assert frame is not None, name
    return frame.findtext("translation"), frame.findtext("orientation")


def test_attach_barbell_to_hands_writes_both_weld_frames() -> None:
    jointset, model = ET.Element("JointSet"), ET.Element("Model")
    left = GripWeld((0.0, -0.05, 0.0), (0.1, 0.2, 0.3), (0.0, 0.0, -0.2))
    right = GripWeld((0.0, -0.05, 0.0), (-0.1, -0.2, 0.3), (0.0, 0.0, 0.2))

    attach_barbell_to_hands(jointset, model, left, right)

    assert _frame(jointset, "barbell_to_left_hand_parent") == (
        "0.000000 -0.050000 0.000000",
        "0.1000000000 0.2000000000 0.3000000000",
    )
    assert _frame(jointset, "barbell_to_left_hand_child") == (
        "0.000000 0.000000 -0.200000",
        "0.000000 0.000000 0.000000",
    )
    assert _frame(model, "barbell_to_right_hand_frame1") == (
        "0.000000 -0.050000 0.000000",
        "-0.1000000000 -0.2000000000 0.3000000000",
    )
    assert _frame(model, "barbell_to_right_hand_frame2")[0] == (
        "0.000000 0.000000 0.200000"
    )


@pytest.mark.parametrize("exercise", GRIP_LIFTS)
def test_spec_grip_welds_hold_the_palms_at_the_spec_grip(exercise: str) -> None:
    left, right = spec_grip_welds(exercise, 1.75)
    half = via_poses.grip_half_width(exercise, 1.75)
    # The left palm is at -Z (canonical +Y) on the shaft, the right at +Z.
    assert math.dist(left.shaft_location, (0, 0, -half)) <= GRIP_CLOSURE_TOL_M
    assert math.dist(right.shaft_location, (0, 0, half)) <= GRIP_CLOSURE_TOL_M
    assert left.hand_location == right.hand_location
    assert left.hand_location[1] < 0  # palm centre is distal along the hand


def test_spec_grip_welds_scale_with_height() -> None:
    left, _ = spec_grip_welds("deadlift", 1.90)
    half = via_poses.grip_half_width("deadlift", 1.90)
    assert half == pytest.approx(
        via_poses.grip_half_width("deadlift", 1.75) * 1.90 / 1.75
    )
    assert math.dist(left.shaft_location, (0, 0, -half)) <= GRIP_CLOSURE_TOL_M


def test_spec_lift_config_defaults_to_the_spec_load() -> None:
    barbell = spec_lift_config("snatch", 80.0, 1.75, None).barbell_spec
    assert barbell.plate_mass_per_side == via_poses.plates_per_side_kg("snatch")
    custom = spec_lift_config("snatch", 80.0, 1.75, 12.5).barbell_spec
    assert custom.plate_mass_per_side == 12.5
