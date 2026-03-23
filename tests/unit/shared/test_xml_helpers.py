"""Tests for XML generation helpers."""

import xml.etree.ElementTree as ET

from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_free_joint,
    add_pin_joint,
    add_weld_joint,
    serialize_model,
    vec3_str,
    vec6_str,
)


class TestVecFormatters:
    def test_vec3_str(self):
        assert vec3_str(1.0, 2.0, 3.0) == "1.000000 2.000000 3.000000"

    def test_vec3_str_negative(self):
        result = vec3_str(-0.5, 0, 0.1)
        assert "-0.500000" in result

    def test_vec6_str(self):
        result = vec6_str(0, 0, 0, 1, 2, 3)
        parts = result.split()
        assert len(parts) == 6


class TestAddBody:
    def test_creates_body_element(self):
        bodyset = ET.Element("BodySet")
        body = add_body(
            bodyset,
            name="test_body",
            mass=10.0,
            mass_center=(0, 0.5, 0),
            inertia_xx=1.0,
            inertia_yy=2.0,
            inertia_zz=3.0,
        )
        assert body.get("name") == "test_body"
        assert body.find("mass").text == "10.000000"
        assert "0.500000" in body.find("mass_center").text

    def test_body_is_child_of_bodyset(self):
        bodyset = ET.Element("BodySet")
        add_body(
            bodyset,
            name="b",
            mass=1.0,
            mass_center=(0, 0, 0),
            inertia_xx=0.1,
            inertia_yy=0.1,
            inertia_zz=0.1,
        )
        assert len(bodyset) == 1
        assert bodyset[0].tag == "Body"


class TestAddPinJoint:
    def test_creates_pin_joint(self):
        jointset = ET.Element("JointSet")
        joint = add_pin_joint(
            jointset,
            name="test_joint",
            parent_body="parent",
            child_body="child",
            location_in_parent=(0, 0, 0),
            location_in_child=(0, 0, 0),
            coord_name="test_flex",
        )
        assert joint.get("name") == "test_joint"
        assert joint.tag == "PinJoint"

    def test_has_coordinate(self):
        jointset = ET.Element("JointSet")
        joint = add_pin_joint(
            jointset,
            name="j",
            parent_body="p",
            child_body="c",
            location_in_parent=(0, 0, 0),
            location_in_child=(0, 0, 0),
            coord_name="flex",
            range_min=-1.0,
            range_max=1.0,
        )
        coord = joint.find(".//Coordinate")
        assert coord is not None
        assert coord.get("name") == "flex"


class TestAddFreeJoint:
    def test_creates_free_joint(self):
        jointset = ET.Element("JointSet")
        joint = add_free_joint(
            jointset,
            name="ground_pelvis",
            parent_body="ground",
            child_body="pelvis",
        )
        assert joint.tag == "FreeJoint"


class TestAddWeldJoint:
    def test_creates_weld_joint(self):
        jointset = ET.Element("JointSet")
        joint = add_weld_joint(
            jointset,
            name="weld",
            parent_body="a",
            child_body="b",
            location_in_parent=(0, 1, 0),
        )
        assert joint.tag == "WeldJoint"


class TestSerializeModel:
    def test_produces_xml_string(self):
        root = ET.Element("OpenSimDocument")
        ET.SubElement(root, "Model", name="test")
        xml_str = serialize_model(root)
        assert "<?xml" in xml_str
        assert "OpenSimDocument" in xml_str
