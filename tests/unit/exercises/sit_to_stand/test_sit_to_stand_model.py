"""Tests for the sit-to-stand model builder."""

import xml.etree.ElementTree as ET

from opensim_models.exercises.sit_to_stand.sit_to_stand_model import (
    SitToStandModelBuilder,
    build_sit_to_stand_model,
)


class TestSitToStandModelBuilder:
    def test_exercise_name(self):
        builder = SitToStandModelBuilder()
        assert builder.exercise_name == "sit_to_stand"

    def test_builds_valid_xml(self):
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_model_has_gravity(self):
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        gravity = root.find(".//gravity")
        assert gravity is not None
        assert "-9.806650" in gravity.text  # type: ignore

    def test_has_chair_body(self):
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "chair" in body_names

    def test_chair_welded_to_ground(self):
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='chair_to_ground']")
        assert weld is not None

    def test_no_barbell_weld_to_torso(self):
        """Sit-to-stand should not have a barbell-to-torso weld joint."""
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_torso']")
        assert weld is None

    def test_custom_seat_height(self):
        builder = SitToStandModelBuilder(seat_height=0.50)
        assert builder.seat_height == 0.50
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        assert root is not None

    def test_has_all_body_segments(self):
        xml_str = SitToStandModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "pelvis" in body_names
        assert "torso" in body_names
        assert "thigh_l" in body_names
        assert "thigh_r" in body_names


class TestBuildSitToStandModel:
    def test_convenience_function(self):
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "sit_to_stand"  # type: ignore

    def test_custom_parameters(self):
        xml_str = build_sit_to_stand_model(
            body_mass=70.0, height=1.65, seat_height=0.40
        )
        root = ET.fromstring(xml_str)
        assert root is not None
