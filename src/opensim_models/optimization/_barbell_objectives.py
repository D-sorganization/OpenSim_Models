"""Objective definitions for barbell exercises (squat, deadlift, bench press).

Phases, timing, phase descriptions and via-poses come from the vendored
exercise spec (standard v2.0, see :mod:`spec_lifts`).
"""

from __future__ import annotations

from opensim_models.optimization.spec_lifts import lift_objective

_HIP_KNEE = ("hip_l_flex", "hip_r_flex", "knee_l_flex", "knee_r_flex")

SQUAT = lift_objective(
    "squat",
    description="Barbell back squat: full depth with hip and knee flexion targets.",
    primary_coordinates=_HIP_KNEE,
)

DEADLIFT = lift_objective(
    "deadlift",
    description="Conventional deadlift from floor to lockout.",
    primary_coordinates=_HIP_KNEE,
)

BENCH_PRESS = lift_objective(
    "bench_press",
    description="Flat barbell bench press: shoulder and elbow movement.",
    primary_coordinates=(
        "shoulder_l_flex",
        "shoulder_r_flex",
        "elbow_l_flex",
        "elbow_r_flex",
    ),
)
