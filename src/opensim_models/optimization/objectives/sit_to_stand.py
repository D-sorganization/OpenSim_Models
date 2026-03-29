from __future__ import annotations

import math
from .core import ExerciseObjective, Phase

SIT_TO_STAND = ExerciseObjective(
    name="sit_to_stand",
    description="Sit-to-stand transfer from chair to upright standing.",
    primary_coordinates=("hip_flexion", "knee_flexion", "ankle_flexion"),
    phases=(
        Phase(
            name="seated",
            time_fraction=0.0,
            joint_targets={
                "hip_flexion": math.radians(90),
                "knee_flexion": math.radians(-90),
                "ankle_flexion": math.radians(10),
            },
            description="Seated position with ~90 deg hip and knee flexion.",
        ),
        Phase(
            name="trunk_flexion",
            time_fraction=0.20,
            joint_targets={
                "hip_flexion": math.radians(110),
                "knee_flexion": math.radians(-90),
                "ankle_flexion": math.radians(15),
            },
            description="Forward trunk lean to shift COM over feet.",
        ),
        Phase(
            name="seat_off",
            time_fraction=0.35,
            joint_targets={
                "hip_flexion": math.radians(90),
                "knee_flexion": math.radians(-75),
                "ankle_flexion": math.radians(20),
            },
            description="Buttocks leave the chair; weight on feet.",
        ),
        Phase(
            name="ascending",
            time_fraction=0.60,
            joint_targets={
                "hip_flexion": math.radians(45),
                "knee_flexion": math.radians(-40),
                "ankle_flexion": math.radians(10),
            },
            description="Extension phase: hips and knees extending.",
        ),
        Phase(
            name="near_standing",
            time_fraction=0.85,
            joint_targets={
                "hip_flexion": math.radians(10),
                "knee_flexion": math.radians(-10),
                "ankle_flexion": math.radians(5),
            },
            description="Nearly upright, decelerating.",
        ),
        Phase(
            name="standing",
            time_fraction=1.0,
            joint_targets={
                "hip_flexion": math.radians(0),
                "knee_flexion": math.radians(0),
                "ankle_flexion": math.radians(0),
            },
            description="Full upright standing posture.",
        ),
    ),
)
