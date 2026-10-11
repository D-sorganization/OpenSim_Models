"""Objective definitions for Olympic lifts (snatch, clean and jerk).

Phases, timing, phase descriptions and via-poses come from the vendored
exercise spec (standard v2.0, see :mod:`spec_lifts`).
"""

from __future__ import annotations

from opensim_models.optimization.spec_lifts import lift_objective

_HIP_KNEE_SHOULDER = (
    "hip_l_flex",
    "hip_r_flex",
    "knee_l_flex",
    "knee_r_flex",
    "shoulder_l_flex",
    "shoulder_r_flex",
)

SNATCH = lift_objective(
    "snatch",
    description="Olympic snatch: barbell from floor to overhead in one motion.",
    primary_coordinates=_HIP_KNEE_SHOULDER,
)

CLEAN_AND_JERK = lift_objective(
    "clean_and_jerk",
    description="Olympic clean and jerk: floor to front rack, then overhead.",
    primary_coordinates=(*_HIP_KNEE_SHOULDER, "elbow_l_flex", "elbow_r_flex"),
)
