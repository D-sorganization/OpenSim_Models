"""Simplified full-body musculoskeletal model for barbell exercises.

Segments (bilateral where noted):
  pelvis, torso, head,
  upper_arm_{l,r}, forearm_{l,r}, hand_{l,r},
  thigh_{l,r}, shank_{l,r}, foot_{l,r}

Joints:
  ground_pelvis (FreeJoint — 6 DOF),
  lumbar (PinJoint — flexion/extension),
  neck (PinJoint),
  shoulder_{l,r} (PinJoint — simplified, flexion only for v0.1),
  elbow_{l,r} (PinJoint),
  wrist_{l,r} (PinJoint),
  hip_{l,r} (PinJoint — flexion/extension),
  knee_{l,r} (PinJoint),
  ankle_{l,r} (PinJoint)

Anthropometric defaults are for a 50th-percentile male (height=1.75 m,
mass=80 kg) following Winter (2009) segment proportions.

Law of Demeter: exercise modules call create_full_body() and receive
body/joint elements — they never manipulate segment internals.
"""

from __future__ import annotations

import logging
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from opensim_models.shared.contracts.preconditions import (
    require_positive,
)
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    rectangular_prism_inertia,
)
from opensim_models.shared.utils.xml_helpers import (
    add_body,
    add_free_joint,
    add_pin_joint,
)

logger = logging.getLogger(__name__)

_TISSUE_DENSITY_KG_M3: float = 1000.0  # Average human tissue ~1000 kg/m³

# Segment names that are themselves bilateral (have _l/_r variants).
# Used to determine whether a child segment's parent link needs a side suffix.
_BILATERAL_SEGMENTS: frozenset[str] = frozenset(
    {"upper_arm", "forearm", "thigh", "shank"}
)


def _segment_radius_from_mass(mass: float, length: float) -> float:
    """Compute cylinder radius from mass and length assuming uniform tissue density.

    Uses: volume = mass/density = π·r²·L → r = sqrt(mass/(density·π·L))
    """
    if length <= 0:
        raise ValueError(f"Segment length must be positive, got {length}")
    if mass <= 0:
        raise ValueError(f"Segment mass must be positive, got {mass}")
    volume = mass / _TISSUE_DENSITY_KG_M3
    return math.sqrt(volume / (math.pi * length))


@dataclass(frozen=True)
class BodyModelSpec:
    """Anthropometric specification for the full-body model.

    All lengths in meters, mass in kg.
    """

    total_mass: float = 80.0
    height: float = 1.75

    def __post_init__(self) -> None:
        require_positive(self.total_mass, "total_mass")
        require_positive(self.height, "height")


# Winter (2009) segment mass fractions and length fractions of total height.
_SEGMENT_TABLE: dict[str, dict[str, float]] = {
    "pelvis": {"mass_frac": 0.142, "length_frac": 0.100},
    "torso": {"mass_frac": 0.355, "length_frac": 0.288},
    "head": {"mass_frac": 0.081, "length_frac": 0.130},
    "upper_arm": {"mass_frac": 0.028, "length_frac": 0.186},
    "forearm": {"mass_frac": 0.016, "length_frac": 0.146},
    "hand": {"mass_frac": 0.006, "length_frac": 0.050},
    "thigh": {"mass_frac": 0.100, "length_frac": 0.245},
    "shank": {"mass_frac": 0.047, "length_frac": 0.246},
    "foot": {"mass_frac": 0.014, "length_frac": 0.040},
}


def _seg(spec: BodyModelSpec, name: str) -> tuple[float, float, float]:
    """Return (mass, length, radius) for a named segment."""
    s = _SEGMENT_TABLE[name]
    seg_mass = spec.total_mass * s["mass_frac"]
    seg_length = spec.height * s["length_frac"]
    radius = _segment_radius_from_mass(seg_mass, seg_length)
    return seg_mass, seg_length, radius


def _add_bilateral_limb(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec,
    *,
    seg_name: str,
    parent_name: str,
    parent_offset_y: float,
    parent_lateral_x: float,
    coord_prefix: str,
    range_min: float,
    range_max: float,
) -> None:
    """Add left and right limb segments with pin joints."""
    mass, length, radius = _seg(spec, seg_name)
    inertia = cylinder_inertia(mass, radius, length)

    for side, sign in [("l", -1.0), ("r", 1.0)]:
        body_name = f"{seg_name}_{side}"
        add_body(
            bodyset,
            name=body_name,
            mass=mass,
            mass_center=(0, -length / 2.0, 0),
            inertia_xx=inertia[0],
            inertia_yy=inertia[1],
            inertia_zz=inertia[2],
        )
        add_pin_joint(
            jointset,
            name=f"{coord_prefix}_{side}",
            parent_body=f"{parent_name}_{side}"
            if parent_name in _BILATERAL_SEGMENTS
            else parent_name,
            child_body=body_name,
            location_in_parent=(sign * parent_lateral_x, parent_offset_y, 0),
            location_in_child=(0, 0, 0),
            coord_name=f"{coord_prefix}_{side}_flex",
            range_min=range_min,
            range_max=range_max,
        )


def create_full_body(
    bodyset: ET.Element,
    jointset: ET.Element,
    spec: BodyModelSpec | None = None,
    *,
    skip_ground_joint: bool = False,
) -> dict[str, ET.Element]:
    """Build the full-body model and append bodies/joints to the given sets.

    Args:
        bodyset: XML element to append Body elements to.
        jointset: XML element to append Joint elements to.
        spec: Anthropometric specification (defaults to 50th-percentile male).
        skip_ground_joint: When True, the FreeJoint connecting pelvis to ground
            is omitted. Use this when another mechanism (e.g. a WeldJoint from
            a bench body) provides the pelvis parent joint, so the body is not
            over-constrained.

    Returns dict of body name -> ET.Element for all created bodies.
    """
    if spec is None:
        spec = BodyModelSpec()

    logger.info(
        "Building full-body model (mass=%.1f kg, height=%.2f m)",
        spec.total_mass,
        spec.height,
    )

    bodies: dict[str, ET.Element] = {}

    # --- Pelvis (connected to ground via FreeJoint) ---
    p_mass, p_len, p_rad = _seg(spec, "pelvis")
    p_inertia = rectangular_prism_inertia(p_mass, p_rad * 2, p_len, p_rad * 2)
    bodies["pelvis"] = add_body(
        bodyset,
        name="pelvis",
        mass=p_mass,
        mass_center=(0, 0, 0),
        inertia_xx=p_inertia[0],
        inertia_yy=p_inertia[1],
        inertia_zz=p_inertia[2],
    )
    # Pelvis height = sum of leg segment lengths (thigh + shank + foot)
    _, thigh_len, _ = _seg(spec, "thigh")
    _, shank_len, _ = _seg(spec, "shank")
    _, foot_len, _ = _seg(spec, "foot")
    pelvis_height = thigh_len + shank_len + foot_len + p_len / 2.0
    logger.debug("Derived pelvis height: %.4f m", pelvis_height)
    if not skip_ground_joint:
        add_free_joint(
            jointset,
            name="ground_pelvis",
            parent_body="ground",
            child_body="pelvis",
            location_in_parent=(0, pelvis_height, 0),
        )

    # --- Torso ---
    t_mass, t_len, t_rad = _seg(spec, "torso")
    t_inertia = rectangular_prism_inertia(t_mass, t_rad * 2, t_len, t_rad * 2)
    bodies["torso"] = add_body(
        bodyset,
        name="torso",
        mass=t_mass,
        mass_center=(0, t_len / 2.0, 0),
        inertia_xx=t_inertia[0],
        inertia_yy=t_inertia[1],
        inertia_zz=t_inertia[2],
    )
    add_pin_joint(
        jointset,
        name="lumbar",
        parent_body="pelvis",
        child_body="torso",
        location_in_parent=(0, p_len / 2.0, 0),
        location_in_child=(0, 0, 0),
        coord_name="lumbar_flex",
        range_min=-0.5236,
        range_max=1.0472,  # ~60° — lower end of clinical range (60–80°)
    )

    # --- Head ---
    h_mass, h_len, h_rad = _seg(spec, "head")
    h_inertia = cylinder_inertia(h_mass, h_rad, h_len)
    bodies["head"] = add_body(
        bodyset,
        name="head",
        mass=h_mass,
        mass_center=(0, h_len / 2.0, 0),
        inertia_xx=h_inertia[0],
        inertia_yy=h_inertia[1],
        inertia_zz=h_inertia[2],
    )
    add_pin_joint(
        jointset,
        name="neck",
        parent_body="torso",
        child_body="head",
        location_in_parent=(0, t_len, 0),
        location_in_child=(0, 0, 0),
        coord_name="neck_flex",
        range_min=-0.5236,
        range_max=0.5236,
    )

    # --- Arms ---
    shoulder_y = t_len * 0.95
    shoulder_x = t_rad * 1.2

    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="upper_arm",
        parent_name="torso",
        parent_offset_y=shoulder_y,
        parent_lateral_x=shoulder_x,
        coord_prefix="shoulder",
        range_min=-3.1416,
        range_max=3.1416,
    )

    _, ua_len, _ = _seg(spec, "upper_arm")
    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="forearm",
        parent_name="upper_arm",
        parent_offset_y=-ua_len,
        parent_lateral_x=0,
        coord_prefix="elbow",
        range_min=0,
        range_max=2.618,
    )

    _, fa_len, _ = _seg(spec, "forearm")
    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="hand",
        parent_name="forearm",
        parent_offset_y=-fa_len,
        parent_lateral_x=0,
        coord_prefix="wrist",
        range_min=-1.2217,
        range_max=1.2217,
    )

    # --- Legs ---
    hip_x = p_rad * 0.6

    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="thigh",
        parent_name="pelvis",
        parent_offset_y=-p_len / 2.0,
        parent_lateral_x=hip_x,
        coord_prefix="hip",
        range_min=-0.5236,
        range_max=2.0944,
    )

    _, th_len, _ = _seg(spec, "thigh")
    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="shank",
        parent_name="thigh",
        parent_offset_y=-th_len,
        parent_lateral_x=0,
        coord_prefix="knee",
        range_min=-2.618,
        range_max=0,
    )

    _, sh_len, _ = _seg(spec, "shank")
    _add_bilateral_limb(
        bodyset,
        jointset,
        spec,
        seg_name="foot",
        parent_name="shank",
        parent_offset_y=-sh_len,
        parent_lateral_x=0,
        coord_prefix="ankle",
        range_min=-0.8727,  # ~-50° plantarflexion (physiological max)
        range_max=0.3491,  # ~+20° dorsiflexion (physiological max)
    )

    logger.info("Full-body model complete: %d bodies created", len(bodies))
    return bodies
