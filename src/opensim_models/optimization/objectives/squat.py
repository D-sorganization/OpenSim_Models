from __future__ import annotations

import math
from .core import ExerciseObjective, Phase

SQUAT = ExerciseObjective(
    name="squat",
    description="Barbell back squat: full depth with hip and knee flexion targets.",
    primary_coordinates=("hip_flexion", "knee_flexion"),
    phases=(
        Phase(
            name="start",
            time_fraction=0.0,
            joint_targets={"hip_flexion": 0.0, "knee_flexion": 0.0},
            description="Standing upright with barbell on back.",
        ),
        Phase(
            name="descent",
            time_fraction=0.25,
            joint_targets={
                "hip_flexion": math.radians(60),
                "knee_flexion": math.radians(-60),
            },
            description="Controlled descent, hips pushing back.",
        ),
        Phase(
            name="bottom",
            time_fraction=0.50,
            joint_targets={
                "hip_flexion": math.radians(120),
                "knee_flexion": math.radians(-120),
            },
            description="Full depth: hip 120 deg flexion, knee -120 deg flexion.",
        ),
        Phase(
            name="drive",
            time_fraction=0.75,
            joint_targets={
                "hip_flexion": math.radians(60),
                "knee_flexion": math.radians(-60),
            },
            description="Driving upward out of the hole.",
        ),
        Phase(
            name="lockout",
            time_fraction=1.0,
            joint_targets={"hip_flexion": 0.0, "knee_flexion": 0.0},
            description="Return to standing lockout.",
        ),
    ),
)
