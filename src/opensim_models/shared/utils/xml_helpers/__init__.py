"""XML generation helpers for OpenSim .osim files.

Public API re-exported from sub-modules for backward compatibility.
"""

from opensim_models.shared.utils.xml_helpers._bodies import add_body
from opensim_models.shared.utils.xml_helpers._formatting import (
    ZERO_VEC3,
    Vec3,
    indent_xml,
    serialize_model,
    vec3_str,
    vec6_str,
)
from opensim_models.shared.utils.xml_helpers._joints import (
    add_ball_joint,
    add_custom_joint,
    add_free_joint,
    add_pin_joint,
    add_weld_joint,
    set_coordinate_default,
)

__all__ = [
    "ZERO_VEC3",
    "Vec3",
    "add_ball_joint",
    "add_body",
    "add_custom_joint",
    "add_free_joint",
    "add_pin_joint",
    "add_weld_joint",
    "indent_xml",
    "serialize_model",
    "set_coordinate_default",
    "vec3_str",
    "vec6_str",
]
