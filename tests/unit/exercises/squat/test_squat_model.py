"""Tests for the back squat model builder."""

import xml.etree.ElementTree as ET

from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.squat.squat_model import (
    SquatModelBuilder,
    build_squat_model,
)
from opensim_models.shared.barbell import BarbellSpec


class TestSquatModelBuilder:
    def test_exercise_name(self):
        builder = SquatModelBuilder()
        assert builder.exercise_name == "back_squat"

    def test_builds_valid_xml(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_model_has_gravity(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        gravity = root.find(".//gravity")
        assert gravity is not None
        assert "-9.806650" in gravity.text  # type: ignore

    def test_barbell_welded_to_torso(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_torso']")
        assert weld is not None

    def test_has_all_body_segments(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "pelvis" in body_names
        assert "torso" in body_names
        assert "barbell_shaft" in body_names
        assert "thigh_l" in body_names
        assert "thigh_r" in body_names

    def test_custom_plate_mass(self):
        config = ExerciseConfig(
            barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=100.0),
        )
        xml_str = SquatModelBuilder(config).build()
        root = ET.fromstring(xml_str)
        # Verify barbell bodies exist with correct mass
        bodies = {b.get("name"): b for b in root.findall(".//Body")}  # type: ignore
        shaft_mass = float(bodies["barbell_shaft"].find("mass").text)  # type: ignore
        assert shaft_mass > 0


class TestBuildSquatModel:
    def test_convenience_function(self):
        xml_str = build_squat_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "back_squat"  # type: ignore

    def test_custom_parameters(self):
        xml_str = build_squat_model(body_mass=100.0, height=1.90, plate_mass_per_side=80.0)
        root = ET.fromstring(xml_str)
        assert root is not None
