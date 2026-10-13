# SPDX-License-Identifier: MIT
"""Unit tests measuring floor-pull bar height above the lowest sole (#416).

Verifies that in the floor-pull lifts (deadlift, snatch, clean and jerk),
the start pose places the barbell center at plate-radius height (0.225 m)
above the lowest foot contact sphere surface on the ground, with both
hand grips satisfied.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.shared.parity import via_poses
from opensim_models.shared.parity._canonical import spec
from opensim_models.shared.parity.standard import STANDARD

PULLS = ("deadlift", "snatch", "clean_and_jerk")
GRIP_TOL_M = 0.005
BAR_HEIGHT_TOL_M = 0.001


@pytest.mark.parametrize("exercise", PULLS)
def test_floor_pull_bar_position_equals_plate_radius(exercise: str) -> None:
    """The bar centre in OpenSim coordinates starts at y = plate radius."""
    plate_radius = (
        spec.exercise_spec(STANDARD, exercise)["load"]["plate_diameter_m"] / 2
    )
    bar_pos = via_poses.bar_position(exercise, "start", 1.75)
    # In OpenSim coordinates, Y is up, so bar_pos[1] is the height above ground
    assert bar_pos[1] == pytest.approx(plate_radius, abs=BAR_HEIGHT_TOL_M)


@pytest.mark.parametrize("exercise", PULLS)
def test_floor_pull_grips_close_on_bar(exercise: str) -> None:
    """Both left and right palm centres close on the bar within grip tolerance."""
    bar_pos = via_poses.bar_position(exercise, "start", 1.75)
    half_width = via_poses.grip_half_width(exercise, 1.75)
    palm_off = via_poses.palm_offset(1.75)

    for side, sign in (("l", -1.0), ("r", 1.0)):
        hand_body = f"hand_{side}"
        origin, rot = via_poses.segment_frame(exercise, "start", hand_body, 1.75)
        palm_pos = origin + rot @ palm_off
        expected_palm = np.array([bar_pos[0], bar_pos[1], sign * half_width])
        dist = float(np.linalg.norm(palm_pos - expected_palm))
        assert dist <= GRIP_TOL_M, (
            f"{exercise} {side}: palm distance {dist * 1000:.2f} mm exceeds tolerance"
        )


@pytest.mark.parametrize("exercise", PULLS)
def test_floor_pull_xml_contains_barbell_weld_to_hand(exercise: str) -> None:
    """The model XML declares the barbell welded to the hand at the start pose."""
    xml_str = EXERCISE_BUILDERS[exercise]()
    root = ET.fromstring(xml_str)
    weld = root.find(".//WeldJoint[@name='barbell_to_left_hand']")
    assert weld is not None, f"{exercise} must weld barbell to hand at start pose"
