"""Ground reaction force (GRF) and centre of pressure (CoP) — engine-free math.

Issue #391. Everything here is in the canonical frame of the vendored parity
standard (Repository_Management#2007): Z up, X forward, Y left, ground plane
z = 0, moments about the world origin. The OpenSim adapter
(``ground_reaction_opensim``) rotates the engine's Y-up records into this frame
with the bundle's ``to_canonical.y_up`` rotation before calling in here.

No contact is explicit: a foot (or the whole body) whose summed vertical force
is at most ``CONTACT_THRESHOLD_N`` reports a zero force and ``cop=None``.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Point2 = tuple[float, float]

# Contact segments of the canonical body, one entry per foot.
FOOT_SEGMENTS: tuple[str, ...] = ("foot_l", "foot_r")
# Smooth (Hertz-smoothed) contact leaks ~1e-9 N with the feet clear of the
# ground; 1 mN is far above that and far below any real support load.
CONTACT_THRESHOLD_N = 1e-3
_ZERO: Vec3 = (0.0, 0.0, 0.0)
_RECORD_AXES = ("X", "Y", "Z")


@dataclass(frozen=True)
class ContactWrench:
    """One contact element's wrench on its contact body (canonical frame)."""

    body: str
    force: Vec3
    moment: Vec3  # about the world origin


@dataclass(frozen=True)
class FootReaction:
    """Ground reaction on one foot, or on the whole body for the total."""

    force: Vec3
    cop: Vec3 | None  # None means no contact (and then force is zero)

    @property
    def in_contact(self) -> bool:
        """True when the ground carries load through this contact."""
        return self.cop is not None


@dataclass(frozen=True)
class GroundReaction:
    """Per-foot and total ground reaction with centres of pressure."""

    feet: dict[str, FootReaction]
    total: FootReaction


def half_space_wrench(
    labels: Sequence[str], values: Sequence[float]
) -> tuple[Vec3, Vec3]:
    """Return (force, moment) the ground exerts on the sphere's body.

    Reads the ``*.HalfSpace.force.{X,Y,Z}`` and ``*.HalfSpace.torque.{X,Y,Z}``
    columns of ``SmoothSphereHalfSpaceForce::getRecordValues`` (the wrench on
    the half-space about the ground origin, engine frame) and negates them.

    Raises:
        ValueError: on a label/value length mismatch, a missing column or a
            non-finite value.
    """
    if len(labels) != len(values):
        raise ValueError(f"{len(labels)} labels but {len(values)} values")
    by_suffix = {
        ".".join(label.rsplit(".", 3)[-3:]): float(value)
        for label, value in zip(labels, values, strict=True)
    }

    def column(kind: str) -> Vec3:
        out = []
        for axis in _RECORD_AXES:
            key = f"HalfSpace.{kind}.{axis}"
            if key not in by_suffix:
                raise ValueError(f"record has no {key} column")
            if not math.isfinite(by_suffix[key]):
                raise ValueError(f"{key} is non-finite")
            out.append(-by_suffix[key])
        return (out[0], out[1], out[2])

    return column("force"), column("torque")


def center_of_pressure(force: Vec3, moment: Vec3) -> Vec3 | None:
    """Point on the ground plane z = 0 where *force* acts, or None if unloaded.

    With p = (px, py, 0), the moment about the origin is p x F plus a free
    moment about z only, so px = -My / Fz and py = Mx / Fz.
    """
    fz = force[2]
    if fz <= CONTACT_THRESHOLD_N:
        return None
    return (-moment[1] / fz, moment[0] / fz, 0.0)


def _sum(vectors: Iterable[Vec3]) -> Vec3:
    x = y = z = 0.0
    for v in vectors:
        x, y, z = x + v[0], y + v[1], z + v[2]
    return (x, y, z)


def _reaction(wrenches: Sequence[ContactWrench]) -> FootReaction:
    force = _sum(w.force for w in wrenches)
    cop = center_of_pressure(force, _sum(w.moment for w in wrenches))
    return FootReaction(force=force if cop is not None else _ZERO, cop=cop)


def ground_reaction(
    wrenches: Iterable[ContactWrench], feet: Sequence[str] = FOOT_SEGMENTS
) -> GroundReaction:
    """Sum contact wrenches per foot and in total; contact on other bodies is not GRF.

    Only feet in contact contribute to the total, so the total force equals the
    sum of the per-foot forces.

    Raises:
        ValueError: if *feet* is empty.
    """
    if not feet:
        raise ValueError("at least one foot segment is required in feet")
    grouped: dict[str, list[ContactWrench]] = {foot: [] for foot in feet}
    for wrench in wrenches:
        if wrench.body in grouped:
            grouped[wrench.body].append(wrench)
    per_foot = {foot: _reaction(ws) for foot, ws in grouped.items()}
    loaded = [
        w for foot, ws in grouped.items() if per_foot[foot].in_contact for w in ws
    ]
    return GroundReaction(feet=per_foot, total=_reaction(loaded))


def _turn(o: Point2, a: Point2, b: Point2) -> float:
    """Z of (a - o) x (b - o): > 0 for a counter-clockwise turn."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def support_polygon(points: Iterable[Point2]) -> list[Point2]:
    """Counter-clockwise convex hull of ground contact points (monotone chain).

    Raises:
        ValueError: if the points do not span an area (fewer than 3 hull points).
    """
    pts = sorted({(float(p[0]), float(p[1])) for p in points})
    lower: list[Point2] = []
    upper: list[Point2] = []
    for chain, ordered in ((lower, pts), (upper, list(reversed(pts)))):
        for p in ordered:
            while len(chain) >= 2 and _turn(chain[-2], chain[-1], p) <= 0:
                chain.pop()
            chain.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:
        raise ValueError(f"support polygon needs 3 non-collinear points, got {hull}")
    return hull


def inside_polygon(point: Sequence[float], polygon: Sequence[Point2]) -> bool:
    """True if *point* lies inside or on a counter-clockwise convex *polygon*.

    Raises:
        ValueError: if *polygon* has fewer than 3 vertices.
    """
    if len(polygon) < 3:
        raise ValueError(f"polygon needs at least 3 vertices, got {len(polygon)}")
    p = (float(point[0]), float(point[1]))
    edges = zip(polygon, [*polygon[1:], polygon[0]], strict=True)
    return all(_turn(a, b, p) >= 0 for a, b in edges)
