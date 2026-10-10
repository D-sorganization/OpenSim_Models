"""Tests for shared exercise-builder helpers in ``exercises.base``."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import attach_barbell_to_hands


class TestAttachBarbellToHandsHandTilt:
    """Issue #426: a grip weld's frame orientation cancels the hand's own
    shoulder-abduct tilt, so the shaft stays level without a wrist
    counter-rotation. ``hand_tilt`` is the ``shoulder_{l,r}_adduct`` value
    (equal for both sides, by construction of every grip exercise)."""

    def test_hand_tilt_defaults_to_zero_orientation(self) -> None:
        """Backward compatibility: omitting ``hand_tilt`` must not change
        any existing caller's generated XML (e.g. bench press, #426)."""
        jointset = ET.Element("JointSet")
        model = ET.Element("Model")

        attach_barbell_to_hands(jointset, 0.4, model)

        left_parent = jointset.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_left_hand_parent']"
        )
        right_frame1 = model.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_right_hand_frame1']"
        )
        assert left_parent is not None
        assert right_frame1 is not None
        assert left_parent.findtext("orientation") == "0.000000 0.000000 0.000000"
        assert right_frame1.findtext("orientation") == "0.000000 0.000000 0.000000"

    def test_hand_tilt_sets_mirrored_orientation_on_both_welds(self) -> None:
        """The left weld's parent (hand_l) frame takes +hand_tilt about X;
        the right weld's frame1 (hand_r) takes -hand_tilt -- the exact
        inverse of each hand's own abduction-tilt rotation, confirmed with
        real-OpenSim FK (hand_l = RotX(-shoulder_l_adduct), hand_r =
        RotX(+shoulder_r_adduct))."""
        jointset = ET.Element("JointSet")
        model = ET.Element("Model")

        attach_barbell_to_hands(jointset, 0.4, model, hand_tilt=-0.5236)

        left_parent = jointset.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_left_hand_parent']"
        )
        left_child = jointset.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_left_hand_child']"
        )
        right_frame1 = model.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_right_hand_frame1']"
        )
        right_frame2 = model.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_right_hand_frame2']"
        )
        assert left_parent is not None
        assert left_child is not None
        assert right_frame1 is not None
        assert right_frame2 is not None

        assert left_parent.findtext("orientation") == "-0.523600 0.000000 0.000000"
        assert right_frame1.findtext("orientation") == "0.523600 0.000000 0.000000"
        # Shaft-side frames carry no orientation offset either way.
        assert left_child.findtext("orientation") == "0.000000 0.000000 0.000000"
        assert right_frame2.findtext("orientation") == "0.000000 0.000000 0.000000"
