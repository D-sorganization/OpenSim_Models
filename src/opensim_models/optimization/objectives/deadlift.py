from __future__ import annotations

import math
from .core import ExerciseObjective, Phase

DEADLIFT = ExerciseObjective(
    name="deadlift",
    description="Conventional deadlift from floor to lockout.",
    primary_coordinates=("hip_flexion", "knee_flexion"),
    phases=(
        Phase(
            name="floor",
            time_fraction=0.0,
            joint_targets={
                "hip_flexion": math.radians(80),
                "knee_flexion": math.radians(-70),
            },
            description="Starting position: hip 80 deg, knee -70 deg.",
        ),
        Phase(
            name="break_floor",
            time_fraction=0.20,
            joint_targets={
                "hip_flexion": math.radians(70),
                "knee_flexion": math.radians(-50),
            },
            description="Bar breaks the floor, knees begin to extend.",
        ),
        Phase(
            name="knee_pass",
            time_fraction=0.45,
            joint_targets={
                "hip_flexion": math.radians(55),
                "knee_flexion": math.radians(-25),
            },
            description="Bar passes the knees; transition to hip extension.",
        ),
        Phase(
            name="hip_drive",
            time_fraction=0.75,
            joint_targets={
                "hip_flexion": math.radians(25),
                "knee_flexion": math.radians(-10),
            },
            description="Hip extension drives the bar upward.",
        ),
        Phase(
            name="lockout",
            time_fraction=1.0,
            joint_targets={"hip_flexion": 0.0, "knee_flexion": 0.0},
            description="Full hip and knee extension at the top.",
        ),
    ),
)
