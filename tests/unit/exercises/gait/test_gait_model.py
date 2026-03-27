"""Tests for the gait (walking) model builder."""

import xml.etree.ElementTree as ET

from opensim_models.exercises.gait.gait_model import (
    GaitModelBuilder,
    build_gait_model,
)


class TestGaitModelBuilder:
    def test_exercise_name(self):
        builder = GaitModelBuilder()
        assert builder.exercise_name == "gait"

    def test_builds_valid_xml(self):
        xml_str = GaitModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_model_has_gravity(self):
        xml_str = GaitModelBuilder().build()
        root = ET.fromstring(xml_str)
        gravity = root.find(".//gravity")
        assert gravity is not None
        assert "-9.806650" in gravity.text  # type: ignore

    def test_no_barbell_weld_to_torso(self):
        """Gait model should not have a barbell-to-torso weld joint."""
        xml_str = GaitModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_torso']")
        assert weld is None

    def test_has_all_body_segments(self):
        xml_str = GaitModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "pelvis" in body_names
        assert "torso" in body_names
        assert "thigh_l" in body_names
        assert "thigh_r" in body_names


class TestBuildGaitModel:
    def test_convenience_function(self):
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "gait"  # type: ignore

    def test_custom_parameters(self):
        xml_str = build_gait_model(body_mass=65.0, height=1.60)
        root = ET.fromstring(xml_str)
        assert root is not None
