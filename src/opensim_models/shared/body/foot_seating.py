"""Seat the foot contact spheres at the contact-law equilibrium depth (#472).

The OpenSim port of MuJoCo_Models ``shared/body/foot_seating.py`` (#447).

Why soles cannot sit exactly on the floor
-----------------------------------------
``SmoothSphereHalfSpaceForce`` is a smoothed Hertz law (see
:func:`opensim_models.shared.contact.static_normal_force`). At zero
penetration a sphere carries only the smoothing force, about 59 N for the pack
spheres, so eight flush spheres carry 0.24 of a 200 kg lifter-and-bar weight
and the model sinks at t = 0.

The static equilibrium is the depth ``delta`` at which the contact forces of
all spheres sum to the supported weight (every body hanging from the pelvis
root: lifter plus bar, not a ground-welded chair). With zero velocity the
force is a function of penetration alone, so ``delta`` is the root of a
monotonic scalar equation and is bisected here without loading OpenSim. The
joints play no part, which is MuJoCo's "hinges held rigid" criterion.

As in MuJoCo the spheres are lowered in their foot frames instead of moving
the root, so a spec start (UpstreamDrift#11743) keeps its via-pose exactly.

Preconditions: a FreeJoint pelvis root, contact spheres named
``foot_{side}_{point}`` and a ``gravity`` element.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from collections.abc import Mapping

from opensim_models.shared.body.ground_placement import (
    contact_heights,
    ground_down_in_body,
)
from opensim_models.shared.contact import foot_sphere_names, static_normal_force
from opensim_models.shared.contracts.preconditions import (
    require_non_negative,
    require_positive,
)

__all__ = [
    "contact_heights",
    "equilibrium_depth",
    "foot_seating_offset",
    "lower_foot_contact_spheres",
    "supported_weight",
]

logger = logging.getLogger(__name__)

_ROOT_BODY = "pelvis"
_MAX_DEPTH_M = 0.05  # bracket upper bound; far beyond any equilibrium
_DEPTH_TOLERANCE_M = 1e-13
_MAX_ITERATIONS = 100
_LOCATION_FORMAT = "{:.9f}"  # 1 nm: keeps the seated force balance to 1e-6


def _parents(model: ET.Element) -> dict[str, str]:
    """Child body -> parent body over every joint (ground parents are '')."""
    parents = {}
    for joint in model.iter():
        if not joint.tag.endswith("Joint"):
            continue
        frames = {
            f.get("name"): (f.findtext("socket_parent") or "").rsplit("/", 1)[-1]
            for f in joint.iter("PhysicalOffsetFrame")
        }
        child = frames.get(joint.findtext("socket_child_frame"))
        parent = frames.get(joint.findtext("socket_parent_frame"))
        if child:
            parents[child] = "" if parent == "ground" else str(parent)
    return parents


def _hangs_from_root(body: str, parents: Mapping[str, str]) -> bool:
    seen = set()
    while body and body not in seen:
        if body == _ROOT_BODY:
            return True
        seen.add(body)
        body = parents.get(body, "")
    return False


def supported_weight(model: ET.Element) -> float:
    """Weight (N) of every body hanging from the pelvis root.

    Lifter and bar count; a body welded to ground (the sit-to-stand chair)
    does not. Postcondition: finite and strictly positive.
    """
    gravity = [float(v) for v in (model.findtext("gravity") or "0 0 0").split()]
    parents = _parents(model)
    mass = sum(
        float(body.findtext("mass") or 0.0)
        for body in model.iter("Body")
        if _hangs_from_root(str(body.get("name")), parents)
    )
    weight = mass * math.sqrt(sum(g * g for g in gravity))
    require_positive(weight, "supported weight")
    return weight


def _contact_force(depth: float, relative: list[float]) -> float:
    return sum(static_normal_force(depth - h) for h in relative)


def equilibrium_depth(heights: Mapping[str, float], weight: float) -> float:
    """Penetration (m) of the lowest sphere at which the contacts carry *weight*.

    *heights* are the sphere surface heights; only their differences matter.
    Spheres higher than the lowest one (a swing foot) contribute their
    smaller force at their own depth.

    Postcondition: ``0 <= result <= 0.05`` and the summed static contact
    force equals *weight* to the bisection tolerance (1e-13 m).

    Raises:
        ValueError: no contact heights, *weight* not positive, or no
            equilibrium in [0, 50] mm (the flush spheres already carry more).
    """
    require_positive(weight, "weight")
    if not heights:
        raise ValueError("equilibrium needs at least one contact height")
    lowest = min(heights.values())
    relative = [h - lowest for h in heights.values()]
    low, high = 0.0, _MAX_DEPTH_M
    if _contact_force(low, relative) >= weight or (
        _contact_force(high, relative) <= weight
    ):
        raise ValueError(
            f"no foot-floor equilibrium for {weight:.1f} N in [0, 50] mm of penetration"
        )
    for _ in range(_MAX_ITERATIONS):
        if high - low < _DEPTH_TOLERANCE_M:
            break
        mid = 0.5 * (low + high)
        if _contact_force(mid, relative) < weight:
            low = mid
        else:
            high = mid
    depth = 0.5 * (low + high)
    logger.debug("Equilibrium foot penetration %.4f mm", depth * 1e3)
    return depth


def foot_seating_offset(model: ET.Element) -> float:
    """Metres to lower the foot spheres so they sit at the equilibrium depth.

    The equilibrium depth minus the deepest sphere's current penetration, so a
    posed start that already penetrates by via-pose rounding is not lowered
    twice.
    """
    heights = contact_heights(model)
    current = -min(heights.values())
    return equilibrium_depth(heights, supported_weight(model)) - current


def lower_foot_contact_spheres(model: ET.Element, depth: float) -> None:
    """Move every foot contact sphere *depth* metres straight down (world -Y).

    Each sphere moves in its foot frame along world down expressed in that
    frame, so a tilted swing foot keeps its height relative to the stance
    foot. Precondition: ``depth >= 0``.
    """
    require_non_negative(depth, "depth")
    names = set(foot_sphere_names())
    for sphere in model.iter("ContactSphere"):
        if sphere.get("name") not in names:
            continue
        location = sphere.find("location")
        if location is None:
            raise ValueError(f"contact sphere {sphere.get('name')!r} has no location")
        body = (sphere.findtext("socket_frame") or "").rsplit("/", 1)[-1]
        down = ground_down_in_body(model, body)
        point = [float(v) for v in (location.text or "0 0 0").split()]
        location.text = " ".join(
            _LOCATION_FORMAT.format(p + depth * d)
            for p, d in zip(point, down, strict=True)
        )
