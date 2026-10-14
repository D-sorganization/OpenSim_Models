"""Tests for the bench press model builder."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.bench_press.bench_press_model import (
    BENCH_HEIGHT,
    BENCH_MASS,
    BenchPressModelBuilder,
    build_bench_press_model,
)


class TestBenchPressModelBuilder:
    def test_exercise_name(self):
        builder = BenchPressModelBuilder()
        assert builder.exercise_name == "bench_press"

    def test_builds_valid_xml(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_barbell_attached_to_hand(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        weld = root.find(".//WeldJoint[@name='barbell_to_left_hand']")
        assert weld is not None

    def test_has_upper_body_segments(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}  # type: ignore
        assert "upper_arm_l" in body_names
        assert "upper_arm_r" in body_names
        assert "forearm_l" in body_names
        assert "hand_l" in body_names

    def test_bench_height_constant(self):
        assert pytest.approx(0.43) == BENCH_HEIGHT

    def test_bench_mass_constant(self):
        assert pytest.approx(1e-4) == BENCH_MASS

    def test_bench_body_mass(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        bench = root.find(".//Body[@name='bench']")
        assert bench is not None
        mass_elem = bench.find("mass")
        assert mass_elem is not None
        assert pytest.approx(1e-4) == float(mass_elem.text or "0")


class TestBuildBenchPressModel:
    def test_convenience_function(self):
        xml_str = build_bench_press_model()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "bench_press"  # type: ignore
