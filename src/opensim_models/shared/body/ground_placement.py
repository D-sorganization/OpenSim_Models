"""Rest-on-ground placement for free-root models (issue #381).

A FreeJoint root left at ``pelvis_ty = 0`` leaves the foot contact spheres far
from the y = 0 half-space. The correct pelvis height is a property of the
generated skeleton and its initial pose, so it is derived here from the model
XML itself: a small forward-kinematics pass from the pelvis to every
``ContactSphere`` (single source of truth, no second copy of the segment table).

Conventions mirror OpenSim 4.x: ``BallJoint`` is body-fixed X-Y-Z, ``PinJoint``
rotates about the joint-frame Z axis, ``CustomJoint`` composes its rotation
``TransformAxis`` elements in order, and offset-frame orientations are body-fixed
X-Y-Z Euler angles.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

from opensim_models.shared.contracts.preconditions import require_positive

Mat = list[list[float]]
Vec = list[float]

_ROOT_BODY = "pelvis"


def _identity() -> Mat:
    return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _matmul(a: Mat, b: Mat) -> Mat:
    return [
        [sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)
    ]


def _apply(rot: Mat, vec: Vec) -> Vec:
    return [sum(rot[i][k] * vec[k] for k in range(3)) for i in range(3)]


def _transpose(rot: Mat) -> Mat:
    return [[rot[j][i] for j in range(3)] for i in range(3)]


def _axis_angle(axis: Vec, angle: float) -> Mat:
    """Rodrigues rotation of *angle* radians about *axis* (normalised here)."""
    norm = math.sqrt(sum(a * a for a in axis))
    x, y, z = (a / norm for a in axis)
    c, s = math.cos(angle), math.sin(angle)
    t = 1.0 - c
    return [
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c],
    ]


def _euler_xyz(angles: Vec) -> Mat:
    """Body-fixed X-Y-Z rotation, as OpenSim reads frame ``orientation``."""
    rot = _identity()
    for axis, angle in zip(((1, 0, 0), (0, 1, 0), (0, 0, 1)), angles, strict=True):
        rot = _matmul(rot, _axis_angle(list(map(float, axis)), angle))
    return rot


def _vec(text: str | None) -> Vec:
    return [float(v) for v in (text or "0 0 0").split()]


def _body_of(frame_path: str | None) -> str:
    return (frame_path or "").rsplit("/", 1)[-1]


class _Frame:
    """An offset frame: rotation and translation relative to its body."""

    def __init__(self, element: ET.Element) -> None:
        self.rot = _euler_xyz(_vec(element.findtext("orientation")))
        self.pos = _vec(element.findtext("translation"))
        self.body = _body_of(element.findtext("socket_parent"))


def _coordinate_values(joint: ET.Element) -> dict[str, float]:
    return {
        str(c.get("name")): float(c.findtext("default_value") or 0.0)
        for c in joint.iter("Coordinate")
    }


def _joint_rotation(joint: ET.Element, values: dict[str, float]) -> Mat:
    """Rotation of the child frame relative to the parent frame at *values*."""
    names = list(values)
    if joint.tag == "PinJoint":
        return _axis_angle([0.0, 0.0, 1.0], values[names[0]])
    if joint.tag == "BallJoint":
        return _euler_xyz([values[n] for n in names[:3]])
    if joint.tag == "CustomJoint":
        rot = _identity()
        for i in (1, 2, 3):
            axis_el = joint.find(f".//TransformAxis[@name='rotation{i}']")
            coord = axis_el.findtext("coordinates") if axis_el is not None else None
            if axis_el is not None and coord:
                axis = _vec(axis_el.findtext("axis"))
                rot = _matmul(rot, _axis_angle(axis, values[coord.strip()]))
        return rot
    if joint.tag == "WeldJoint":
        return _identity()
    raise ValueError(f"unsupported joint type for ground placement: {joint.tag}")


def _frame_named(joint: ET.Element, socket: str) -> _Frame:
    name = joint.findtext(socket)
    for frame in joint.iter("PhysicalOffsetFrame"):
        if frame.get("name") == name:
            return _Frame(frame)
    raise ValueError(f"joint {joint.get('name')!r} has no frame {name!r}")


def _pose_in_pelvis(
    body: str, joints_by_child: dict[str, ET.Element]
) -> tuple[Mat, Vec]:
    """Rotation and origin of *body* expressed in the pelvis frame."""
    rot, pos = _identity(), [0.0, 0.0, 0.0]
    while body != _ROOT_BODY:
        joint = joints_by_child.get(body)
        if joint is None:
            raise ValueError(f"body {body!r} is not attached to the pelvis")
        parent = _frame_named(joint, "socket_parent_frame")
        child = _frame_named(joint, "socket_child_frame")
        q = _joint_rotation(joint, _coordinate_values(joint))
        # child body -> parent body: p_parent = P + Rp Rq (Rc^T p_child - Rc^T c)
        r_cb = _transpose(child.rot)
        shift = _apply(r_cb, [-v for v in child.pos])
        rot_pb = _matmul(_matmul(parent.rot, q), r_cb)
        origin = [
            a + b
            for a, b in zip(
                parent.pos, _apply(_matmul(parent.rot, q), shift), strict=True
            )
        ]
        pos = [a + b for a, b in zip(origin, _apply(rot_pb, pos), strict=True)]
        rot = _matmul(rot_pb, rot)
        body = parent.body
    return rot, pos


def _joints_by_child(model: ET.Element) -> dict[str, ET.Element]:
    jointset = model.find("JointSet")
    if jointset is None:
        raise ValueError("model needs a JointSet and ContactSphere geometry")
    return {
        _frame_named(j, "socket_child_frame").body: j
        for j in jointset.iter()
        if j.tag.endswith("Joint") and j.tag != "FreeJoint"
    }


def _sphere_lows_in_pelvis(model: ET.Element) -> dict[str, Vec]:
    """Lowest point of every contact sphere in the pelvis frame (pelvis upright).

    "Lowest" is along the pelvis -Y axis, which is world -Y for an upright
    pelvis; :func:`contact_heights` corrects for a rotated root.
    """
    joints_by_child = _joints_by_child(model)
    spheres = list(model.iter("ContactSphere"))
    if not spheres:
        raise ValueError("model needs a JointSet and ContactSphere geometry")
    lows = {}
    for sphere in spheres:
        radius = float(sphere.findtext("radius") or 0.0)
        require_positive(radius, "Contact sphere radius")
        rot, pos = _pose_in_pelvis(
            _body_of(sphere.findtext("socket_frame")), joints_by_child
        )
        centre = _apply(rot, _vec(sphere.findtext("location")))
        lows[str(sphere.get("name"))] = [
            pos[0] + centre[0],
            pos[1] + centre[1],
            pos[2] + centre[2],
            radius,
        ]
    return lows


def lowest_contact_height_below_pelvis(model: ET.Element) -> float:
    """Return the lowest contact-sphere surface height relative to the pelvis.

    Evaluated at the current coordinate defaults with the pelvis upright
    (identity orientation). The value is negative when the feet hang below the
    pelvis. Precondition: *model* has a ``JointSet`` and contact spheres.
    """
    return min(c[1] - c[3] for c in _sphere_lows_in_pelvis(model).values())


def _root_pose(model: ET.Element) -> tuple[Mat, Vec]:
    """Pelvis rotation and origin in ground from the FreeJoint defaults.

    Body-fixed X-Y-Z rotation, then translation in the ground frame:
    ``p_ground = P + Rp (t + Rq Rc^T (p_pelvis - c))`` as for the other joints.
    """
    root = model.find("JointSet//FreeJoint")
    if root is None:
        raise ValueError("model has no free (FreeJoint) pelvis root")
    values = list(_coordinate_values(root).values())
    parent = _frame_named(root, "socket_parent_frame")
    child = _frame_named(root, "socket_child_frame")
    r_pq = _matmul(parent.rot, _euler_xyz(values[:3]))
    shift = _apply(_transpose(child.rot), [-v for v in child.pos])
    origin = [
        p + t + s
        for p, t, s in zip(
            parent.pos,
            _apply(parent.rot, values[3:6]),
            _apply(r_pq, shift),
            strict=True,
        )
    ]
    return _matmul(r_pq, _transpose(child.rot)), origin


def contact_heights(model: ET.Element) -> dict[str, float]:
    """World height (y) of every contact sphere's lowest point, by sphere name.

    Evaluated at the coordinate defaults, including the pelvis FreeJoint pose.
    Negative values penetrate the y = 0 floor.

    Raises:
        ValueError: no FreeJoint root, JointSet or contact spheres.
    """
    rot, origin = _root_pose(model)
    return {
        name: origin[1] + _apply(rot, centre[:3])[1] - centre[3]
        for name, centre in _sphere_lows_in_pelvis(model).items()
    }


def ground_down_in_body(model: ET.Element, body: str) -> Vec:
    """World -Y (down) expressed in *body*'s frame at the coordinate defaults.

    Raises:
        ValueError: no FreeJoint root, or *body* does not hang from the pelvis.
    """
    root_rot, _ = _root_pose(model)
    rot, _ = _pose_in_pelvis(body, _joints_by_child(model))
    return _apply(_transpose(_matmul(root_rot, rot)), [0.0, -1.0, 0.0])


def standing_pelvis_height(model: ET.Element) -> float:
    """Pelvis height above y = 0 at which the lowest foot sphere just touches.

    Postcondition: the result is finite and strictly positive.
    """
    height = -lowest_contact_height_below_pelvis(model)
    if not math.isfinite(height) or height <= 0.0:
        raise AssertionError(f"derived pelvis height {height!r} m is not positive")
    return height
