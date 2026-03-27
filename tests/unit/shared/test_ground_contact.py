"""Tests for ground contact geometry and force elements."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.bench_press.bench_press_model import (
    BenchPressModelBuilder,
)
from opensim_models.exercises.squat.squat_model import SquatModelBuilder
from opensim_models.shared.utils.xml_helpers import (
    add_contact_half_space,
    add_contact_sphere,
    add_hunt_crossley_force,
)


class TestContactHalfSpace:
    def test_creates_element(self):
        model = ET.Element("Model")
        geom = add_contact_half_space(model, name="ground_contact", body="ground")
        assert geom.tag == "ContactHalfSpace"
        assert geom.get("name") == "ground_contact"

    def test_socket_frame_ground(self):
        model = ET.Element("Model")
        geom = add_contact_half_space(model, name="gc", body="ground")
        assert geom.find("socket_frame").text == "/ground"

    def test_socket_frame_non_ground(self):
        model = ET.Element("Model")
        geom = add_contact_half_space(model, name="bc", body="bench")
        assert geom.find("socket_frame").text == "/bodyset/bench"

    def test_creates_contact_geometry_set(self):
        model = ET.Element("Model")
        add_contact_half_space(model)
        cg_set = model.find("ContactGeometrySet")
        assert cg_set is not None
        assert len(cg_set) == 1

    def test_reuses_existing_contact_geometry_set(self):
        model = ET.Element("Model")
        add_contact_half_space(model, name="gc1")
        add_contact_half_space(model, name="gc2", body="bench")
        cg_sets = model.findall("ContactGeometrySet")
        assert len(cg_sets) == 1
        assert len(cg_sets[0]) == 2


class TestContactSphere:
    def test_creates_element(self):
        model = ET.Element("Model")
        geom = add_contact_sphere(model, name="foot_l_heel", body="foot_l", location=(0, 0, 0))
        assert geom.tag == "ContactSphere"
        assert geom.get("name") == "foot_l_heel"

    def test_has_radius(self):
        model = ET.Element("Model")
        geom = add_contact_sphere(model, name="cs", body="foot_l", location=(0, 0, 0), radius=0.03)
        assert geom.find("radius").text == "0.030000"

    def test_rejects_nonpositive_radius(self):
        model = ET.Element("Model")
        with pytest.raises(ValueError, match="positive"):
            add_contact_sphere(model, name="bad", body="foot_l", location=(0, 0, 0), radius=0.0)

    def test_has_location(self):
        model = ET.Element("Model")
        geom = add_contact_sphere(model, name="cs", body="foot_l", location=(0.1, -0.02, -0.03))
        loc_text = geom.find("location").text
        assert "0.100000" in loc_text
        assert "-0.020000" in loc_text


class TestHuntCrossleyForce:
    def test_creates_element(self):
        model = ET.Element("Model")
        force = add_hunt_crossley_force(
            model,
            name="force_foot",
            contact_geometry_1="foot_sphere",
            contact_geometry_2="ground_contact",
        )
        assert force.tag == "HuntCrossleyForce"
        assert force.get("name") == "force_foot"

    def test_has_contact_geometry_refs(self):
        model = ET.Element("Model")
        force = add_hunt_crossley_force(
            model,
            name="f",
            contact_geometry_1="s1",
            contact_geometry_2="s2",
        )
        assert force.find("contact_geometry_1").text == "s1"
        assert force.find("contact_geometry_2").text == "s2"

    def test_has_default_parameters(self):
        model = ET.Element("Model")
        force = add_hunt_crossley_force(
            model,
            name="f",
            contact_geometry_1="s1",
            contact_geometry_2="s2",
        )
        assert float(force.find("stiffness").text) == pytest.approx(1e7)
        assert float(force.find("dissipation").text) == pytest.approx(0.5)
        assert float(force.find("static_friction").text) == pytest.approx(0.8)

    def test_creates_force_set(self):
        model = ET.Element("Model")
        add_hunt_crossley_force(model, name="f", contact_geometry_1="a", contact_geometry_2="b")
        fs = model.find("ForceSet")
        assert fs is not None
        assert len(fs) == 1

    def test_reuses_existing_force_set(self):
        model = ET.Element("Model")
        add_hunt_crossley_force(model, name="f1", contact_geometry_1="a", contact_geometry_2="b")
        add_hunt_crossley_force(model, name="f2", contact_geometry_1="c", contact_geometry_2="d")
        force_sets = model.findall("ForceSet")
        assert len(force_sets) == 1
        assert len(force_sets[0]) == 2


class TestExerciseModelGroundContact:
    """Integration tests: verify contact elements appear in built models."""

    def test_squat_has_contact_geometry_set(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        cg_set = root.find(".//ContactGeometrySet")
        assert cg_set is not None

    def test_squat_has_ground_half_space(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        half_space = root.find(".//ContactHalfSpace[@name='ground_contact']")
        assert half_space is not None

    def test_squat_has_eight_foot_contact_spheres(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        spheres = root.findall(".//ContactSphere")
        # 8 foot contact spheres (4 per foot)
        assert len(spheres) == 8

    def test_squat_has_hunt_crossley_forces(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        forces = root.findall(".//HuntCrossleyForce")
        # 8 forces (one per foot contact sphere)
        assert len(forces) == 8

    def test_squat_force_set_exists(self):
        xml_str = SquatModelBuilder().build()
        root = ET.fromstring(xml_str)
        force_set = root.find(".//ForceSet")
        assert force_set is not None

    def test_bench_press_has_bench_contact(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        bench_half_space = root.find(".//ContactHalfSpace[@name='bench_contact']")
        assert bench_half_space is not None

    def test_bench_press_has_pelvis_contact_sphere(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        pelvis_sphere = root.find(".//ContactSphere[@name='pelvis_contact']")
        assert pelvis_sphere is not None

    def test_bench_press_has_pelvis_bench_force(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        force = root.find(".//HuntCrossleyForce[@name='force_pelvis_bench']")
        assert force is not None

    def test_bench_press_total_contact_spheres(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        spheres = root.findall(".//ContactSphere")
        # 8 foot + 1 pelvis = 9
        assert len(spheres) == 9

    def test_bench_press_total_forces(self):
        xml_str = BenchPressModelBuilder().build()
        root = ET.fromstring(xml_str)
        forces = root.findall(".//HuntCrossleyForce")
        # 8 foot + 1 pelvis-bench = 9
        assert len(forces) == 9
