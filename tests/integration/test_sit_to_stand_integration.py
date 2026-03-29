"""Integration tests for sit-to-stand model: end-to-end build and structure."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.sit_to_stand.sit_to_stand_model import (
    build_sit_to_stand_model,
)


class TestSitToStandIntegration:
    """Verify the sit-to-stand model builds correctly with chair body."""

    def test_build_produces_valid_xml(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_no_barbell_bodies(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        assert "barbell_shaft" not in body_names

    def test_has_chair_body(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        assert "chair" in body_names

    def test_chair_welded_to_ground(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        weld_names = {j.get("name") for j in root.findall(".//WeldJoint")}
        assert "chair_to_ground" in weld_names

    def test_initial_pose_seated(self) -> None:
        """Initial pose should have ~90 deg hip and knee flexion."""
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        defaults: dict[str, float] = {}
        for coord in root.iter("Coordinate"):
            name = coord.get("name", "")
            dv = coord.find("default_value")
            if dv is not None and dv.text:
                defaults[name] = float(dv.text)
        # Hip flexion should be near 90 deg (1.5708 rad)
        assert abs(defaults.get("hip_l_flex", 0.0) - 1.5708) < 0.01
        assert abs(defaults.get("hip_r_flex", 0.0) - 1.5708) < 0.01

    def test_has_ground_pelvis_free_joint(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        free_joints = root.findall(".//FreeJoint")
        names = {j.get("name") for j in free_joints}
        assert "ground_pelvis" in names

    @pytest.mark.parametrize("seat_height", [0.40, 0.45, 0.55])
    def test_different_seat_heights(self, seat_height: float) -> None:
        xml_str = build_sit_to_stand_model(seat_height=seat_height)
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_has_foot_contact_spheres(self) -> None:
        xml_str = build_sit_to_stand_model()
        root = ET.fromstring(xml_str)
        sphere_names = {s.get("name") for s in root.findall(".//ContactSphere")}
        for side in ("l", "r"):
            assert f"foot_{side}_heel_medial" in sphere_names
