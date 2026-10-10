"""Cross-repo parity standard -- canonical biomechanical parameters.

Every value is computed from the vendored canonical bundle
(``_canonical/biomech_parity_standard.json``); nothing is duplicated here.
"""

from __future__ import annotations

import logging
from typing import Any

from opensim_models.shared.parity._canonical import conformance

logger = logging.getLogger(__name__)

STANDARD: dict[str, Any] = conformance.load_standard()

_ANTHRO: dict[str, Any] = STANDARD["anthropometrics"]
_SEGMENTS: dict[str, dict[str, Any]] = _ANTHRO["segments"]

STANDARD_BODY_MASS: float = float(_ANTHRO["body_mass_kg"])
STANDARD_HEIGHT: float = float(_ANTHRO["height_m"])

SEGMENT_MASS_FRACTIONS: dict[str, float] = {
    name: float(seg["mass_frac"]) for name, seg in _SEGMENTS.items()
}

SEGMENT_LENGTH_FRACTIONS: dict[str, float] = {
    name: float(seg["length_frac"]) for name, seg in _SEGMENTS.items()
}

SEGMENT_RADIUS_FRACTIONS: dict[str, float] = {
    name: float(seg["radius_frac"]) for name, seg in _SEGMENTS.items()
}


# Side-less coordinate name (``hip_flex``) -> (lower_rad, upper_rad); the
# bundle expresses both sides with one ``{side}`` template, so they share limits.
_SIDE0: str = STANDARD["sides"][0]
_EXPECTED_COORDS = conformance.expected_coordinates(STANDARD)
JOINT_LIMITS: dict[str, tuple[float, float]] = {
    c["name"].replace("_{side}", ""): _EXPECTED_COORDS[c["name"].format(side=_SIDE0)]
    for c in STANDARD["coordinates"]
}

_BARBELL: dict[str, float] = STANDARD["barbell"]["mens"]
MENS_BARBELL: dict[str, float] = {
    "total_length": float(_BARBELL["total_length_m"]),
    "shaft_length": float(_BARBELL["shaft_length_m"]),
    "shaft_diameter": float(_BARBELL["shaft_diameter_m"]),
    "sleeve_diameter": float(_BARBELL["sleeve_diameter_m"]),
    "bar_mass": float(_BARBELL["bar_mass_kg"]),
}

FOOT_CONTACT_DIMS: dict[str, float] = {
    k: float(v) for k, v in STANDARD["contact"]["foot_box_m"].items()
}

GROUND_FRICTION: dict[str, float] = {
    k: float(v) for k, v in STANDARD["contact"]["ground_friction"].items()
}

# Keyed by this repo's legacy exercise key where the bundle defines one
# (``back_squat``), otherwise by the exercise id.
EXERCISE_PHASE_COUNTS: dict[str, int] = {
    str(ex.get("legacy_key", name)): int(ex["phase_count"])
    for name, ex in STANDARD["exercises"].items()
}

# OpenSim is a Y-up engine: gravity points along -Y.
GRAVITY: tuple[float, float, float] = (
    0.0,
    -float(STANDARD["frame"]["gravity_mps2"]),
    0.0,
)
