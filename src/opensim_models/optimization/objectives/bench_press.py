from __future__ import annotations

import math
from .core import ExerciseObjective, Phase

BENCH_PRESS = ExerciseObjective(
    name="bench_press",
    description="Flat barbell bench press: shoulder and elbow movement.",
    primary_coordinates=("shoulder_flexion", "elbow_flexion"),
    phases=(
        Phase(
            name="lockout_top",
            time_fraction=0.0,
            joint_targets={
                "shoulder_flexion": math.radians(90),
                "elbow_flexion": 0.0,
            },
            description="Arms locked out at the top; shoulder 90 deg flexion.",
        ),
        Phase(
            name="descent",
            time_fraction=0.25,
            joint_targets={
                "shoulder_flexion": math.radians(70),
                "elbow_flexion": math.radians(45),
            },
            description="Controlled eccentric lowering of the bar.",
        ),
        Phase(
            name="chest",
            time_fraction=0.50,
            joint_targets={
                "shoulder_flexion": math.radians(45),
                "elbow_flexion": math.radians(90),
            },
            description="Bar at chest level; elbow 90 deg flexion.",
        ),
        Phase(
            name="press",
            time_fraction=0.75,
            joint_targets={
                "shoulder_flexion": math.radians(70),
                "elbow_flexion": math.radians(45),
            },
            description="Pressing the bar back up.",
        ),
        Phase(
            name="lockout",
            time_fraction=1.0,
            joint_targets={
                "shoulder_flexion": math.radians(90),
                "elbow_flexion": 0.0,
            },
            description="Return to full lockout.",
        ),
    ),
)
