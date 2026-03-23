"""Tests for barbell model generation."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.shared.barbell import BarbellSpec, create_barbell_bodies


class TestBarbellSpec:
    def test_mens_defaults(self):
        spec = BarbellSpec.mens_olympic()
        assert spec.total_length == 2.20
        assert spec.bar_mass == 20.0
        assert spec.shaft_diameter == 0.028
        assert spec.plate_mass_per_side == 0.0

    def test_womens_defaults(self):
        spec = BarbellSpec.womens_olympic()
        assert spec.total_length == 2.01
        assert spec.bar_mass == 15.0
        assert spec.shaft_diameter == 0.025

    def test_sleeve_length(self):
        spec = BarbellSpec.mens_olympic()
        expected = (2.20 - 1.31) / 2.0
        assert spec.sleeve_length == pytest.approx(expected)

    def test_total_mass_with_plates(self):
        spec = BarbellSpec.mens_olympic(plate_mass_per_side=60.0)
        assert spec.total_mass == pytest.approx(140.0)

    def test_shaft_mass_proportional(self):
        spec = BarbellSpec.mens_olympic()
        assert spec.shaft_mass == pytest.approx(20.0 * 1.31 / 2.20)

    def test_rejects_negative_plate_mass(self):
        with pytest.raises(ValueError, match="non-negative"):
            BarbellSpec(plate_mass_per_side=-1.0)

    def test_rejects_shaft_longer_than_total(self):
        with pytest.raises(ValueError, match="shaft_length"):
            BarbellSpec(total_length=1.0, shaft_length=1.5)

    def test_rejects_zero_diameter(self):
        with pytest.raises(ValueError, match="must be positive"):
            BarbellSpec(shaft_diameter=0.0)

    def test_frozen(self):
        spec = BarbellSpec.mens_olympic()
        with pytest.raises(AttributeError):
            spec.bar_mass = 25.0


class TestCreateBarbellBodies:
    @pytest.fixture()
    def sets(self):
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        return bodyset, jointset

    def test_creates_three_bodies(self, sets):
        bodyset, jointset = sets
        spec = BarbellSpec.mens_olympic()
        bodies = create_barbell_bodies(bodyset, jointset, spec)
        assert len(bodies) == 3
        assert "barbell_shaft" in bodies
        assert "barbell_left_sleeve" in bodies
        assert "barbell_right_sleeve" in bodies

    def test_creates_two_weld_joints(self, sets):
        bodyset, jointset = sets
        spec = BarbellSpec.mens_olympic()
        create_barbell_bodies(bodyset, jointset, spec)
        welds = jointset.findall("WeldJoint")
        assert len(welds) == 2

    def test_custom_prefix(self, sets):
        bodyset, jointset = sets
        spec = BarbellSpec.mens_olympic()
        bodies = create_barbell_bodies(bodyset, jointset, spec, prefix="bar")
        assert "bar_shaft" in bodies

    def test_mass_conservation(self, sets):
        bodyset, jointset = sets
        spec = BarbellSpec.mens_olympic(plate_mass_per_side=50.0)
        create_barbell_bodies(bodyset, jointset, spec)
        total = sum(float(b.find("mass").text) for b in bodyset.findall("Body"))
        assert total == pytest.approx(spec.total_mass, rel=1e-4)
