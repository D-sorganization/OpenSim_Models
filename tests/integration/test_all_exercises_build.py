"""Integration tests: verify all five exercise models build end-to-end.

Each model must produce well-formed XML with the correct structure:
OpenSimDocument > Model > (gravity, Ground, BodySet, JointSet).
"""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.bench_press.bench_press_model import (
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import build_deadlift_model
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model

ALL_BUILDERS = [
    ("back_squat", build_squat_model),
    ("bench_press", build_bench_press_model),
    ("deadlift", build_deadlift_model),
    ("snatch", build_snatch_model),
    ("clean_and_jerk", build_clean_and_jerk_model),
]


class TestAllExercisesBuild:
    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_produces_valid_xml(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_model_name_matches(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        model = root.find("Model")
        assert model.get("name") == name

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_has_gravity(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        gravity = root.find(".//gravity")
        assert gravity is not None
        assert "-9.806650" in gravity.text

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_has_bodies_and_joints(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        assert root.find(".//BodySet") is not None
        assert root.find(".//JointSet") is not None

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_minimum_body_count(self, name, builder):
        """Every exercise should have at least 18 bodies (15 body + 3 barbell)."""
        xml_str = builder()
        root = ET.fromstring(xml_str)
        bodies = root.findall(".//Body")
        assert len(bodies) >= 18

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_all_masses_positive(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        for body in root.findall(".//Body"):
            mass = float(body.find("mass").text)
            assert mass > 0, f"{body.get('name')} mass={mass}"

    @pytest.mark.parametrize(
        "name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS]
    )
    def test_barbell_present(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        assert "barbell_shaft" in body_names
        assert "barbell_left_sleeve" in body_names
        assert "barbell_right_sleeve" in body_names
