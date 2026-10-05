"""Bilateral limb construction helpers for the full-body model.

DRY: These functions create symmetric left/right limb pairs with the
appropriate joint types. Used by ``body_model.create_full_body``.

Axes follow the canonical frame mapped to OpenSim's Y-up frame: X is forward,
Z is lateral (right = +Z, left = -Z, i.e. canonical left = +Y), Y is up. A
coordinate marked ``mirror`` gives its axis for the right side and is negated
on the left, so equal left/right values make a symmetric pose (#383).
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

from opensim_models.shared.body._segment_data import (
    _BILATERAL_SEGMENTS,
    BodyModelSpec,
    _seg,
)
from opensim_models.shared.utils.geometry import cylinder_inertia
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_custom_joint,
    add_pin_joint,
)

logger = logging.getLogger(__name__)

_SIDES: tuple[tuple[str, float], ...] = (("l", -1.0), ("r", 1.0))


def _side_axis(axis: str, side: str, *, mirror: bool) -> str:
    """Return *axis* (given for the right side), negated on the left if mirrored."""
    if not mirror or side == "r":
        return axis
    return " ".join(str(-float(v) + 0.0) for v in axis.split())


def _resolve_parent_name(parent_name: str, side: str) -> str:
    """Return the side-qualified parent name for bilateral segments."""
    return (
        f"{parent_name}_{side}" if parent_name in _BILATERAL_SEGMENTS else parent_name
    )


def _add_bilateral_body(
    bodyset: ET.Element,
    seg_name: str,
    side: str,
    mass: float,
    length: float,
    inertia: tuple[float, float, float],
    bodies: dict[str, ET.Element] | None,
) -> str:
    """Add one side's body element and register it in *bodies*. Returns body name."""
    body_name = f"{seg_name}_{side}"
    body_el = add_body(
        bodyset,
        name=body_name,
        mass=mass,
        mass_center=(0, -length / 2.0, 0),
        inertia_xx=inertia[0],
        inertia_yy=inertia[1],
        inertia_zz=inertia[2],
    )
    if bodies is not None:
        bodies[body_name] = body_el
    return body_name


def add_bilateral_limb(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    *,
    seg_name: str,
    parent_name: str,
    parent_offset_y: float,
    parent_lateral_z: float,
    coord_prefix: str,
    range_min: float,
    range_max: float,
    bodies: dict[str, ET.Element] | None = None,
) -> None:
    """Add left and right limb segments with pin joints."""
    mass, length, radius = _seg(spec, seg_name)
    inertia = cylinder_inertia(mass, radius, length)

    for side, sign in _SIDES:
        body_name = _add_bilateral_body(
            bodyset, seg_name, side, mass, length, inertia, bodies
        )
        add_pin_joint(
            jointset,
            name=f"{coord_prefix}_{side}",
            parent_body=_resolve_parent_name(parent_name, side),
            child_body=body_name,
            location_in_parent=(0, parent_offset_y, sign * parent_lateral_z),
            location_in_child=(0, 0, 0),
            coord_name=f"{coord_prefix}_{side}_flex",
            range_min=range_min,
            range_max=range_max,
        )


def add_bilateral_custom_joint_limb(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    *,
    seg_name: str,
    parent_name: str,
    parent_offset_y: float,
    parent_lateral_z: float,
    coord_prefix: str,
    coord_defs: list[dict[str, str | float]],
    bodies: dict[str, ET.Element] | None = None,
) -> None:
    """Add left and right limb segments with CustomJoints (N-DOF).

    Each entry of *coord_defs* has ``suffix``, ``range_min``, ``range_max`` and
    optionally ``default_value``, ``axis`` (right-side axis) and ``mirror``.
    """
    mass, length, radius = _seg(spec, seg_name)
    inertia = cylinder_inertia(mass, radius, length)

    for side, sign in _SIDES:
        body_name = _add_bilateral_body(
            bodyset, seg_name, side, mass, length, inertia, bodies
        )
        coordinates: list[dict[str, float | str]] = [
            {
                "name": f"{coord_prefix}_{side}_{c['suffix']}",
                "default_value": float(c.get("default_value", 0.0)),
                "range_min": float(c["range_min"]),
                "range_max": float(c["range_max"]),
                # No default axis here: add_custom_joint assigns distinct ones.
                **(
                    {
                        "axis": _side_axis(
                            str(c["axis"]), side, mirror=bool(c.get("mirror"))
                        )
                    }
                    if "axis" in c
                    else {}
                ),
            }
            for c in coord_defs
        ]
        add_custom_joint(
            jointset,
            name=f"{coord_prefix}_{side}",
            parent_body=_resolve_parent_name(parent_name, side),
            child_body=body_name,
            location_in_parent=(0, parent_offset_y, sign * parent_lateral_z),
            location_in_child=(0, 0, 0),
            coordinates=coordinates,
        )
