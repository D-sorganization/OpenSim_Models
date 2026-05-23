"""XML generation helpers for OpenSim .osim files.

.. deprecated::
    This module has been split into a sub-package under
    ``opensim_models.shared.utils.xml_helpers``. Import from the package
    instead. This shim re-exports the public API for backward compatibility.
"""

from opensim_models.shared.utils.xml_helpers import (  # noqa: F401
    ZERO_VEC3,
    Vec3,
    add_ball_joint,
    add_body,
    add_custom_joint,
    add_free_joint,
    add_pin_joint,
    add_weld_joint,
    float_str,
    indent_xml,
    serialize_model,
    set_coordinate_default,
    vec3_str,
    vec6_str,
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
    "float_str",
    "indent_xml",
    "serialize_model",
    "set_coordinate_default",
    "vec3_str",
    "vec6_str",
]
