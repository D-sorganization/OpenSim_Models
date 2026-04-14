"""Tests for full-body model generation."""

import xml.etree.ElementTree as ET

import pytest

from opensim_models.shared.body import BodyModelSpec, create_full_body


class TestBodyModelSpec:
    def test_defaults(self):
        spec = BodyModelSpec()
        assert spec.total_mass == 80.0  # type: ignore
        assert spec.height == 1.75

    def test_rejects_zero_mass(self):
        with pytest.raises(ValueError, match="must be positive"):
            BodyModelSpec(total_mass=0.0)

    def test_rejects_negative_height(self):
        with pytest.raises(ValueError, match="must be positive"):
            BodyModelSpec(height=-1.0)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_mass(self, value):
        with pytest.raises(ValueError, match="non-finite"):
            BodyModelSpec(total_mass=value)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_height(self, value):
        with pytest.raises(ValueError, match="non-finite"):
            BodyModelSpec(height=value)

    def test_frozen(self):
        spec = BodyModelSpec()
        with pytest.raises(AttributeError):
            spec.total_mass = 100.0  # type: ignore


class TestCreateFullBody:
    @pytest.fixture()
    def model_elements(self):
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        bodies = create_full_body(bodyset, jointset)
        return bodyset, jointset, bodies

    def test_creates_pelvis(self, model_elements):
        _, _, bodies = model_elements
        assert "pelvis" in bodies

    def test_creates_torso(self, model_elements):
        _, _, bodies = model_elements
        assert "torso" in bodies

    def test_creates_head(self, model_elements):
        _, _, bodies = model_elements
        assert "head" in bodies

    def test_creates_bilateral_arms(self, model_elements):
        bodyset, _, _ = model_elements
        names = {b.get("name") for b in bodyset.findall("Body")}  # type: ignore
        for seg in ["upper_arm", "forearm", "hand"]:
            assert f"{seg}_l" in names
            assert f"{seg}_r" in names

    def test_creates_bilateral_legs(self, model_elements):
        bodyset, _, _ = model_elements
        names = {b.get("name") for b in bodyset.findall("Body")}  # type: ignore
        for seg in ["thigh", "shank", "foot"]:
            assert f"{seg}_l" in names
            assert f"{seg}_r" in names

    def test_total_body_count(self, model_elements):
        bodyset, _, _ = model_elements
        # pelvis + torso + head + 2*(upper_arm + forearm + hand + thigh + shank + foot)
        # = 3 + 2*6 = 15 bodies
        assert len(bodyset.findall("Body")) == 15

    def test_has_ground_pelvis_free_joint(self, model_elements):
        _, jointset, _ = model_elements
        free_joints = jointset.findall("FreeJoint")
        names = [j.get("name") for j in free_joints]  # type: ignore
        assert "ground_pelvis" in names

    def test_hip_is_ball_joint(self, model_elements):
        _, jointset, _ = model_elements
        ball_joints = jointset.findall("BallJoint")
        names = [j.get("name") for j in ball_joints]  # type: ignore
        assert "hip_l" in names
        assert "hip_r" in names

    def test_shoulder_is_ball_joint(self, model_elements):
        _, jointset, _ = model_elements
        ball_joints = jointset.findall("BallJoint")
        names = [j.get("name") for j in ball_joints]  # type: ignore
        assert "shoulder_l" in names
        assert "shoulder_r" in names

    def test_lumbar_is_ball_joint(self, model_elements):
        _, jointset, _ = model_elements
        ball_joints = jointset.findall("BallJoint")
        names = [j.get("name") for j in ball_joints]  # type: ignore
        assert "lumbar" in names

    def test_ankle_is_custom_joint(self, model_elements):
        _, jointset, _ = model_elements
        custom_joints = jointset.findall("CustomJoint")
        names = [j.get("name") for j in custom_joints]  # type: ignore
        assert "ankle_l" in names
        assert "ankle_r" in names

    def test_wrist_is_custom_joint(self, model_elements):
        _, jointset, _ = model_elements
        custom_joints = jointset.findall("CustomJoint")
        names = [j.get("name") for j in custom_joints]  # type: ignore
        assert "wrist_l" in names
        assert "wrist_r" in names

    def test_hip_has_three_coordinates(self, model_elements):
        _, jointset, _ = model_elements
        for ball in jointset.findall("BallJoint"):
            if ball.get("name") == "hip_r":
                coords = ball.findall(".//Coordinate")
                assert len(coords) == 3
                coord_names = {c.get("name") for c in coords}
                assert "hip_r_flex" in coord_names
                assert "hip_r_adduct" in coord_names
                assert "hip_r_rotate" in coord_names

    def test_ankle_has_two_coordinates(self, model_elements):
        _, jointset, _ = model_elements
        for cj in jointset.findall("CustomJoint"):
            if cj.get("name") == "ankle_r":
                coords = cj.findall(".//Coordinate")
                assert len(coords) == 2
                coord_names = {c.get("name") for c in coords}
                assert "ankle_r_flex" in coord_names
                assert "ankle_r_inversion" in coord_names

    def test_all_masses_positive(self, model_elements):
        bodyset, _, _ = model_elements
        for body in bodyset.findall("Body"):
            mass = float(body.find("mass").text)  # type: ignore
            assert mass > 0, f"{body.get('name')} has non-positive mass {mass}"  # type: ignore

    def test_custom_spec(self):
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        spec = BodyModelSpec(total_mass=100.0, height=1.90)
        bodies = create_full_body(bodyset, jointset, spec)
        # Pelvis mass should scale with total mass
        pelvis_mass = float(bodies["pelvis"].find("mass").text)  # type: ignore
        assert pelvis_mass == pytest.approx(100.0 * 0.142)
