"""Dedicated tests for bilateral limb builder helpers."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import BodyModelSpec
from opensim_models.shared.body.limb_builders import (
    add_bilateral_ball_joint_limb,
    add_bilateral_custom_joint_limb,
    add_bilateral_limb,
)


class TestAddBilateralLimb:
    """Pin-joint builder should create symmetric left/right limbs."""

    def test_creates_side_specific_bodies_and_joints(self) -> None:
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        bodies: dict[str, ET.Element] = {}
        spec = BodyModelSpec(total_mass=80.0, height=1.75)

        add_bilateral_limb(
            bodyset,
            jointset,
            spec,
            seg_name="shank",
            parent_name="thigh",
            parent_offset_y=-0.42,
            parent_lateral_x=0.08,
            coord_prefix="knee",
            range_min=-2.5,
            range_max=0.1,
            bodies=bodies,
        )

        assert set(bodies) == {"shank_l", "shank_r"}
        assert {body.get("name") for body in bodyset.findall("Body")} == {
            "shank_l",
            "shank_r",
        }

        left_joint = jointset.find("PinJoint[@name='knee_l']")
        right_joint = jointset.find("PinJoint[@name='knee_r']")
        assert left_joint is not None
        assert right_joint is not None
        assert left_joint.find("PhysicalOffsetFrame[@name='knee_l_parent']") is not None
        assert (
            right_joint.find("PhysicalOffsetFrame[@name='knee_r_parent']") is not None
        )

        assert (
            left_joint.find(
                "PhysicalOffsetFrame[@name='knee_l_parent']/socket_parent"
            ).text
            == "/bodyset/thigh_l"
        )  # type: ignore[union-attr]
        assert (
            right_joint.find(
                "PhysicalOffsetFrame[@name='knee_r_parent']/socket_parent"
            ).text
            == "/bodyset/thigh_r"
        )  # type: ignore[union-attr]
        assert (
            left_joint.find(
                "PhysicalOffsetFrame[@name='knee_l_parent']/translation"
            ).text
            == "-0.080000 -0.420000 0.000000"
        )  # type: ignore[union-attr]
        assert (
            right_joint.find(
                "PhysicalOffsetFrame[@name='knee_r_parent']/translation"
            ).text
            == "0.080000 -0.420000 0.000000"
        )  # type: ignore[union-attr]
        assert left_joint.find(".//Coordinate").get("name") == "knee_l_flex"  # type: ignore[union-attr]
        assert right_joint.find(".//Coordinate").get("name") == "knee_r_flex"  # type: ignore[union-attr]


class TestAddBilateralBallJointLimb:
    """Ball-joint builder should emit three coordinates per side."""

    def test_creates_three_coordinate_ball_joints(self) -> None:
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        spec = BodyModelSpec(total_mass=75.0, height=1.80)

        add_bilateral_ball_joint_limb(
            bodyset,
            jointset,
            spec,
            seg_name="upper_arm",
            parent_name="torso",
            parent_offset_y=0.33,
            parent_lateral_x=0.11,
            coord_prefix="shoulder",
            coord_suffixes=("flex", "adduct", "rotate"),
            ranges=(
                (-1.0, 2.0),
                (-0.5, 0.5),
                (-0.75, 0.75),
            ),
        )

        for side, sign in [("l", -1.0), ("r", 1.0)]:
            joint = jointset.find(f"BallJoint[@name='shoulder_{side}']")
            assert joint is not None
            assert (
                joint.find(
                    f"PhysicalOffsetFrame[@name='shoulder_{side}_parent']/socket_parent"
                ).text
                == "/bodyset/torso"
            )  # type: ignore[union-attr]
            assert (
                joint.find(
                    f"PhysicalOffsetFrame[@name='shoulder_{side}_parent']/translation"
                ).text
                == f"{sign * 0.110000:.6f} 0.330000 0.000000"
            )  # type: ignore[union-attr]

            coords = joint.findall(".//Coordinate")
            assert [c.get("name") for c in coords] == [
                f"shoulder_{side}_flex",
                f"shoulder_{side}_adduct",
                f"shoulder_{side}_rotate",
            ]
            assert [c.find("range").text for c in coords] == [  # type: ignore[union-attr]
                "-1.000000 2.000000",
                "-0.500000 0.500000",
                "-0.750000 0.750000",
            ]


class TestAddBilateralCustomJointLimb:
    """Custom-joint builder should preserve per-axis metadata."""

    def test_creates_custom_joint_coordinates_and_axes(self) -> None:
        bodyset = ET.Element("BodySet")
        jointset = ET.Element("JointSet")
        spec = BodyModelSpec(total_mass=68.0, height=1.72)

        add_bilateral_custom_joint_limb(
            bodyset,
            jointset,
            spec,
            seg_name="foot",
            parent_name="shank",
            parent_offset_y=-0.39,
            parent_lateral_x=0.0,
            coord_prefix="ankle",
            coord_defs=[
                {
                    "suffix": "flex",
                    "default_value": 0.1,
                    "range_min": -0.2,
                    "range_max": 0.8,
                    "axis": "0 0 1",
                },
                {
                    "suffix": "inversion",
                    "range_min": -0.3,
                    "range_max": 0.3,
                },
            ],
        )

        for side in ("l", "r"):
            joint = jointset.find(f"CustomJoint[@name='ankle_{side}']")
            assert joint is not None
            assert (
                joint.find(
                    f"PhysicalOffsetFrame[@name='ankle_{side}_parent']/socket_parent"
                ).text
                == f"/bodyset/shank_{side}"
            )  # type: ignore[union-attr]

            coords = joint.findall(".//Coordinate")
            assert [c.get("name") for c in coords] == [
                f"ankle_{side}_flex",
                f"ankle_{side}_inversion",
            ]
            assert coords[0].find("default_value").text == "0.100000"  # type: ignore[union-attr]
            assert coords[0].find("range").text == "-0.200000 0.800000"  # type: ignore[union-attr]
            assert coords[1].find("default_value").text == "0.000000"  # type: ignore[union-attr]
            assert coords[1].find("range").text == "-0.300000 0.300000"  # type: ignore[union-attr]

            axes = [
                axis.find("axis").text
                for axis in joint.findall("SpatialTransform/TransformAxis")
            ]  # type: ignore[union-attr]
            assert axes == ["0 0 1", "0 0 1"]
