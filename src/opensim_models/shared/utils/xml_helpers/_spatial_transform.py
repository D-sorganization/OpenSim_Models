"""CustomJoint <SpatialTransform> construction (six TransformAxis, OpenSim 4.x).

OpenSim requires all six axes on a CustomJoint and rejects collinear rotation
axes; this module builds a complete, valid transform from a coordinate list.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

_BASIS_AXES: tuple[str, ...] = ("1 0 0", "0 1 0", "0 0 1")
# Default axis of the i-th rotation coordinate when none is given (distinct).
_DEFAULT_ROTATION_AXES: tuple[str, ...] = ("0 0 1", "1 0 0", "0 1 0")


def _parse_axis(text: str) -> tuple[float, float, float]:
    x, y, z = (float(v) for v in text.split())
    return (x, y, z)


def _collinear(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    cross = (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
    return all(abs(c) < 1e-9 for c in cross)


def _fill_rotation_axes(driven: list[str]) -> list[str]:
    """Return 3 mutually non-collinear rotation axes, keeping *driven* first."""
    axes = list(driven)
    for basis in _BASIS_AXES:
        if len(axes) == 3:
            break
        if not any(_collinear(_parse_axis(basis), _parse_axis(a)) for a in axes):
            axes.append(basis)
    return axes


def _add_transform_axis(
    spatial: ET.Element, name: str, axis: str, coord_name: str | None
) -> None:
    """Append one TransformAxis, driven linearly by *coord_name* (or constant 0)."""
    ta = ET.SubElement(spatial, "TransformAxis", name=name)
    if coord_name is not None:
        ET.SubElement(ta, "coordinates").text = coord_name
    ET.SubElement(ta, "axis").text = axis
    func = ET.SubElement(ta, "function")
    if coord_name is None:
        ET.SubElement(ET.SubElement(func, "Constant"), "value").text = "0"
    else:
        lin = ET.SubElement(func, "LinearFunction")
        ET.SubElement(lin, "coefficients").text = "1 0"


def _require_distinct_rotation_axes(driven: list[str]) -> None:
    """Precondition: no two driven rotation axes are collinear."""
    for i, a in enumerate(driven):
        if any(_collinear(_parse_axis(a), _parse_axis(b)) for b in driven[:i]):
            raise ValueError(
                f"CustomJoint rotation axes must not be collinear: {driven}"
            )


def _coordinate_name(coords: list[dict[str, float | str]], i: int) -> str | None:
    """Name of the i-th coordinate, or None when that axis is undriven."""
    return str(coords[i]["name"]) if i < len(coords) else None


def _translation_axis(coords: list[dict[str, float | str]], i: int) -> str:
    return (
        str(coords[i].get("axis", _BASIS_AXES[i]))
        if i < len(coords)
        else _BASIS_AXES[i]
    )


def _add_spatial_transform(
    joint: ET.Element,
    coordinates: list[dict[str, float | str]],
) -> None:
    """Append a complete <SpatialTransform> (6 TransformAxis) to a CustomJoint.

    OpenSim requires all six axes and rejects collinear rotation axes. The first
    three coordinates drive rotations (in the supplied axes), later ones drive
    translations; unused rotations get orthogonal constant-zero axes.
    """
    if len(coordinates) > 6:
        raise ValueError(
            f"CustomJoint supports at most 6 coordinates, got {len(coordinates)}"
        )
    spatial = ET.SubElement(joint, "SpatialTransform")
    rot, trans = coordinates[:3], coordinates[3:]
    driven = [str(c.get("axis", _DEFAULT_ROTATION_AXES[i])) for i, c in enumerate(rot)]
    _require_distinct_rotation_axes(driven)
    rot_axes = _fill_rotation_axes(driven)
    for i in range(3):
        _add_transform_axis(
            spatial, f"rotation{i + 1}", rot_axes[i], _coordinate_name(rot, i)
        )
    for i in range(3):
        _add_transform_axis(
            spatial,
            f"translation{i + 1}",
            _translation_axis(trans, i),
            _coordinate_name(trans, i),
        )
