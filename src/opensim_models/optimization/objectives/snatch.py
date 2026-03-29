from __future__ import annotations

import math
from .core import ExerciseObjective, Phase

SNATCH = ExerciseObjective(
    name="snatch",
    description="Olympic snatch: barbell from floor to overhead in one motion.",
    primary_coordinates=("hip_flexion", "knee_flexion", "shoulder_flexion"),
    phases=(
        Phase(
            name="first_pull",
            time_fraction=0.0,
            joint_targets={
                "hip_flexion": math.radians(80),
                "knee_flexion": math.radians(-70),
                "shoulder_flexion": math.radians(-10),
            },
            description="Starting position on the floor, shoulders over bar.",
        ),
        Phase(
            name="transition",
            time_fraction=0.20,
            joint_targets={
                "hip_flexion": math.radians(60),
                "knee_flexion": math.radians(-40),
                "shoulder_flexion": math.radians(0),
            },
            description="Bar passes knees, knees re-bend slightly.",
        ),
        Phase(
            name="second_pull",
            time_fraction=0.40,
            joint_targets={
                "hip_flexion": math.radians(10),
                "knee_flexion": math.radians(-10),
                "shoulder_flexion": math.radians(60),
            },
            description="Explosive triple extension driving bar upward.",
        ),
        Phase(
            name="turnover",
            time_fraction=0.55,
            joint_targets={
                "hip_flexion": math.radians(30),
                "knee_flexion": math.radians(-30),
                "shoulder_flexion": math.radians(150),
            },
            description="Pulling under the bar, rotating arms overhead.",
        ),
        Phase(
            name="catch_overhead",
            time_fraction=0.75,
            joint_targets={
                "hip_flexion": math.radians(100),
                "knee_flexion": math.radians(-100),
                "shoulder_flexion": math.radians(180),
            },
            description="Receiving the bar in deep overhead squat.",
        ),
        Phase(
            name="recovery",
            time_fraction=1.0,
            joint_targets={
                "hip_flexion": 0.0,
                "knee_flexion": 0.0,
                "shoulder_flexion": math.radians(180),
            },
            description="Standing up from the catch to full extension.",
        ),
    ),
)
