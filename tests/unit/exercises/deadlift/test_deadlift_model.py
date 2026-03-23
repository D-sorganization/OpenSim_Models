"""Tests for the deadlift model builder."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.deadlift.deadlift_model import (
    PLATE_RADIUS,
    DeadliftModelBuilder,
    build_deadlift_model,
)


class TestDeadliftModelBuilder:
    def test_exercise_name(self):
        assert DeadliftModelBuilder().exercise_name == "deadlift"

    def test_builds_valid_xml(self):
        xml_str = DeadliftModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_barbell_attached_to_hand(self):
        xml_str = DeadliftModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_left_hand']")
        assert weld is not None

    def test_plate_radius_standard(self):
        assert pytest.approx(0.225) == PLATE_RADIUS

    def test_has_lower_body_segments(self):
        xml_str = DeadliftModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        assert "thigh_l" in body_names
        assert "shank_l" in body_names
        assert "foot_l" in body_names


class TestBuildDeadliftModel:
    def test_convenience_function(self):
        xml_str = build_deadlift_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "deadlift"

    def test_default_plate_mass(self):
        xml_str = build_deadlift_model(plate_mass_per_side=80.0)
        root = ET.fromstring(xml_str)
        assert root is not None
