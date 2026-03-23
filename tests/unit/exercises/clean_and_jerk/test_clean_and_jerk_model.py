"""Tests for the clean and jerk model builder."""

import xml.etree.ElementTree as ET

from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    CleanAndJerkModelBuilder,
    build_clean_and_jerk_model,
)


class TestCleanAndJerkModelBuilder:
    def test_exercise_name(self):
        assert CleanAndJerkModelBuilder().exercise_name == "clean_and_jerk"

    def test_builds_valid_xml(self):
        xml_str = CleanAndJerkModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_shoulder_width_grip(self):
        xml_str = CleanAndJerkModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_left_hand']")
        assert weld is not None

    def test_has_all_segments_for_full_motion(self):
        xml_str = CleanAndJerkModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        # Clean and jerk needs everything
        for seg in ["pelvis", "torso", "head"]:
            assert seg in body_names
        for seg in ["upper_arm", "forearm", "hand", "thigh", "shank", "foot"]:
            assert f"{seg}_l" in body_names
            assert f"{seg}_r" in body_names

    def test_total_body_count(self):
        """15 body segments + 3 barbell parts = 18 total."""
        xml_str = CleanAndJerkModelBuilder().build()
        root = ET.fromstring(xml_str)
        bodies = root.findall(".//Body")
        assert len(bodies) == 18


class TestBuildCleanAndJerkModel:
    def test_convenience_function(self):
        xml_str = build_clean_and_jerk_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "clean_and_jerk"

    def test_custom_mass(self):
        xml_str = build_clean_and_jerk_model(body_mass=90.0, plate_mass_per_side=60.0)
        root = ET.fromstring(xml_str)
        assert root is not None
