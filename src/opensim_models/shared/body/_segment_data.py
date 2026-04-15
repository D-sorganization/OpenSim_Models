"""Anthropometric segment data and helpers.

DRY: Constants and helper functions used by both ``body_model`` and
``limb_builders`` are centralised here to avoid circular imports.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from opensim_models.shared.contracts.preconditions import require_positive

logger = logging.getLogger(__name__)

_TISSUE_DENSITY_KG_M3: float = 1000.0  # Average human tissue ~1000 kg/m^3

# Segment names that are themselves bilateral (have _l/_r variants).
_BILATERAL_SEGMENTS: frozenset[str] = frozenset(
    {"upper_arm", "forearm", "thigh", "shank"}
)


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


def _segment_radius_from_mass(mass: float, length: float) -> float:
    """Compute cylinder radius from mass and length assuming uniform tissue density.

    Uses: volume = mass/density = pi * r^2 * L  =>  r = sqrt(mass / (density * pi * L))

    Note on usage for non-cylindrical segments (issues #58, #59):
      - Limb segments (upper_arm, forearm, thigh, shank, etc.) use this radius
        directly with ``cylinder_inertia`` -- a good geometric match.
      - The pelvis and torso use this radius as a *half-width* input to
        ``rectangular_prism_inertia(mass, 2*r, length, 2*r)``.  This produces
        a square cross-section whose half-width equals the cylinder radius.
        The resulting inertia values are ~4/pi times larger than the cylinder
        (square vs circle cross-section), which is intentional: the pelvis and
        torso are broader than a cylinder of equal mass and length.  This is a
        deliberate simplification, not a bug.

    Rejects non-finite (NaN / +/-inf) and non-positive values via
    ``require_positive`` (issue #151).
    """
    require_positive(length, "Segment length")
    require_positive(mass, "Segment mass")
    volume = mass / _TISSUE_DENSITY_KG_M3
    return math.sqrt(volume / (math.pi * length))


def _seg(spec: BodyModelSpec, name: str) -> tuple[float, float, float]:
    """Return (mass, length, radius) for a named segment."""
    s = _SEGMENT_TABLE[name]
    seg_mass = spec.total_mass * s["mass_frac"]
    seg_length = spec.height * s["length_frac"]
    radius = _segment_radius_from_mass(seg_mass, seg_length)
    return seg_mass, seg_length, radius
