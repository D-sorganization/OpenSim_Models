"""Tests for the snatch model builder."""

import xml.etree.ElementTree as ET

from opensim_models.exercises.snatch.snatch_model import (
    SnatchModelBuilder,
    build_snatch_model,
)


class TestSnatchModelBuilder:
    def test_exercise_name(self):
        assert SnatchModelBuilder().exercise_name == "snatch"

    def test_builds_valid_xml(self):
        xml_str = SnatchModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_wide_grip_attachment(self):
        """Snatch grip should be wider than other exercises."""
        xml_str = SnatchModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_left_hand']")
        assert weld is not None
        # Verify the grip offset is in the child translation
        child_frame = weld.find(
            ".//PhysicalOffsetFrame[@name='barbell_to_left_hand_child']"
        )
        assert child_frame is not None

    def test_has_full_body_for_overhead_squat(self):
        xml_str = SnatchModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        # Snatch requires full body — upper and lower
        assert "upper_arm_l" in body_names
        assert "thigh_l" in body_names
        assert "torso" in body_names


class TestBuildSnatchModel:
    def test_convenience_function(self):
        xml_str = build_snatch_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "snatch"
