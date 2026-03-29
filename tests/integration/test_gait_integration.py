"""Integration tests for gait model: end-to-end build and structure validation."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises.gait.gait_model import build_gait_model


class TestGaitIntegration:
    """Verify the gait model builds correctly and has expected structure."""

    def test_build_produces_valid_xml(self) -> None:
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_no_barbell_bodies(self) -> None:
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        body_names = {b.get("name") for b in root.findall(".//Body")}
        assert "barbell_shaft" not in body_names
        assert "barbell_left_sleeve" not in body_names
        assert "barbell_right_sleeve" not in body_names

    def test_has_ground_pelvis_free_joint(self) -> None:
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        free_joints = root.findall(".//FreeJoint")
        names = {j.get("name") for j in free_joints}
        assert "ground_pelvis" in names

    def test_has_bilateral_leg_joints(self) -> None:
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        all_joint_names: set[str] = set()
        for tag in ("PinJoint", "BallJoint", "CustomJoint"):
            for j in root.findall(f".//{tag}"):
                all_joint_names.add(j.get("name", ""))
        for side in ("l", "r"):
            assert f"hip_{side}" in all_joint_names
            assert f"knee_{side}" in all_joint_names
            assert f"ankle_{side}" in all_joint_names

    def test_has_foot_contact_spheres(self) -> None:
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        sphere_names = {s.get("name") for s in root.findall(".//ContactSphere")}
        for side in ("l", "r"):
            for point in ("heel_medial", "heel_lateral", "toe_medial", "toe_lateral"):
                assert f"foot_{side}_{point}" in sphere_names

    def test_initial_pose_asymmetric(self) -> None:
        """Gait model should have asymmetric stance/swing leg defaults."""
        xml_str = build_gait_model()
        root = ET.fromstring(xml_str)
        defaults: dict[str, float] = {}
        for coord in root.iter("Coordinate"):
            name = coord.get("name", "")
            dv = coord.find("default_value")
            if dv is not None and dv.text:
                defaults[name] = float(dv.text)
        # Right leg (stance) and left leg (swing) should differ
        assert abs(defaults.get("hip_r_flex", 0.0)) < abs(
            defaults.get("hip_l_flex", 0.0)
        ), "Swing leg (left) should have larger hip flexion than stance (right)"

    @pytest.mark.parametrize("mass", [50.0, 80.0, 120.0])
    def test_different_body_masses(self, mass: float) -> None:
        xml_str = build_gait_model(body_mass=mass)
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_custom_height(self) -> None:
        xml_str = build_gait_model(height=1.60)
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"
