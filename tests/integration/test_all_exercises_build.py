"""Integration tests: verify all exercise models build end-to-end.

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
from opensim_models.exercises.gait.gait_model import build_gait_model
from opensim_models.exercises.sit_to_stand.sit_to_stand_model import (
    build_sit_to_stand_model,
)
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model

# Exercises that use a barbell (barbell-specific assertions apply).
_BARBELL_EXERCISES = {"back_squat", "bench_press", "deadlift", "snatch", "clean_and_jerk"}

ALL_BUILDERS = [
    ("back_squat", build_squat_model),
    ("bench_press", build_bench_press_model),
    ("deadlift", build_deadlift_model),
    ("snatch", build_snatch_model),
    ("clean_and_jerk", build_clean_and_jerk_model),
    ("gait", build_gait_model),
    ("sit_to_stand", build_sit_to_stand_model),
]


class TestAllExercisesBuild:
    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_produces_valid_xml(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_model_name_matches(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        model = root.find("Model")
        assert model.get("name") == name  # type: ignore

    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_has_gravity(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        gravity = root.find(".//gravity")
        assert gravity is not None
        assert "-9.806650" in gravity.text  # type: ignore

    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_has_bodies_and_joints(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        assert root.find(".//BodySet") is not None  # type: ignore
        assert root.find(".//JointSet") is not None  # type: ignore

    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_minimum_body_count(self, name, builder):
        """Barbell exercises: >= 18 bodies (15 body + 3 barbell).
        Non-barbell exercises: >= 15 bodies.
        """
        xml_str = builder()
        root = ET.fromstring(xml_str)
        bodies = root.findall(".//Body")
        if name in _BARBELL_EXERCISES:
            assert len(bodies) >= 18
        else:
            assert len(bodies) >= 15

    @pytest.mark.parametrize("name,builder", ALL_BUILDERS, ids=[n for n, _ in ALL_BUILDERS])
    def test_all_masses_positive(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        for body in root.findall(".//Body"):
            mass = float(body.find("mass").text)  # type: ignore
            assert mass > 0, f"{body.get('name')} mass={mass}"  # type: ignore

    @pytest.mark.parametrize(
        "name,builder",
        [b for b in ALL_BUILDERS if b[0] in _BARBELL_EXERCISES],
        ids=[n for n, _ in ALL_BUILDERS if n in _BARBELL_EXERCISES],
    )
    def test_barbell_present(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "barbell_shaft" in body_names
        assert "barbell_left_sleeve" in body_names
        assert "barbell_right_sleeve" in body_names

    @pytest.mark.parametrize(
        "name,builder",
        [b for b in ALL_BUILDERS if b[0] not in _BARBELL_EXERCISES],
        ids=[n for n, _ in ALL_BUILDERS if n not in _BARBELL_EXERCISES],
    )
    def test_no_barbell_for_non_barbell_exercises(self, name, builder):
        xml_str = builder()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "barbell_shaft" not in body_names
