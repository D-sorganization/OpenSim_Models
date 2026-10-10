"""Tests for WeldConstraint XML generation helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from opensim_models.shared.utils.constraint_helpers import add_weld_constraint


class TestAddWeldConstraint:
    def test_creates_weld_constraint(self) -> None:
        model = ET.Element("Model")
        weld = add_weld_constraint(
            model,
            name="weld",
            body_1="hand_r",
            body_2="barbell_shaft",
            location_in_body_1=(0, 0, 0),
            location_in_body_2=(0, 0, 0.4),
        )
        assert weld.tag == "WeldConstraint"
        assert weld.get("name") == "weld"

    def test_rejects_identical_bodies(self) -> None:
        model = ET.Element("Model")
        with pytest.raises(ValueError, match="distinct bodies"):
            add_weld_constraint(
                model,
                name="weld",
                body_1="a",
                body_2="a",
                location_in_body_1=(0, 0, 0),
                location_in_body_2=(0, 0, 0),
            )

    def test_orientation_defaults_to_zero(self) -> None:
        """Backward compatibility: omitting the new orientation kwargs must
        not change any existing caller's generated XML (issue #426)."""
        model = ET.Element("Model")
        add_weld_constraint(
            model,
            name="weld",
            body_1="hand_r",
            body_2="barbell_shaft",
            location_in_body_1=(0, 0, 0),
            location_in_body_2=(0, 0, 0.4),
        )
        frame_1 = model.find(".//PhysicalOffsetFrame[@name='weld_frame1']")
        frame_2 = model.find(".//PhysicalOffsetFrame[@name='weld_frame2']")
        assert frame_1 is not None
        assert frame_2 is not None
        assert frame_1.findtext("orientation") == "0.000000 0.000000 0.000000"
        assert frame_2.findtext("orientation") == "0.000000 0.000000 0.000000"

    def test_orientation_in_body_1_is_set_on_frame1(self) -> None:
        """Issue #426: the right-hand WeldConstraint's frame on hand_r can
        carry an orientation offset that cancels the hand's own tilt, so
        the constraint's orientation row is satisfied without a wrist
        counter-rotation."""
        model = ET.Element("Model")
        add_weld_constraint(
            model,
            name="barbell_to_right_hand",
            body_1="hand_r",
            body_2="barbell_shaft",
            location_in_body_1=(0, 0, 0),
            location_in_body_2=(0, 0, 0.4),
            orientation_in_body_1=(0.5236, 0.0, 0.0),
        )
        frame_1 = model.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_right_hand_frame1']"
        )
        frame_2 = model.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_right_hand_frame2']"
        )
        assert frame_1 is not None
        assert frame_2 is not None
        assert frame_1.findtext("orientation") == "0.523600 0.000000 0.000000"
        assert frame_2.findtext("orientation") == "0.000000 0.000000 0.000000"
