"""Objective definitions for Olympic lifts (snatch, clean and jerk)."""

from __future__ import annotations

import math

from opensim_models.optimization._types import ExerciseObjective, Phase

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

CLEAN_AND_JERK = ExerciseObjective(
    name="clean_and_jerk",
    description="Olympic clean and jerk: floor to front rack, then overhead.",
    primary_coordinates=(
        "hip_flexion",
        "knee_flexion",
        "shoulder_flexion",
        "elbow_flexion",
    ),
    phases=(
        Phase(
            name="clean_setup",
            time_fraction=0.0,
            joint_targets={
                "hip_flexion": math.radians(80),
                "knee_flexion": math.radians(-70),
                "shoulder_flexion": math.radians(-10),
                "elbow_flexion": 0.0,
            },
            description="Starting position on the floor.",
        ),
        Phase(
            name="clean_first_pull",
            time_fraction=0.12,
            joint_targets={
                "hip_flexion": math.radians(60),
                "knee_flexion": math.radians(-45),
                "shoulder_flexion": math.radians(0),
                "elbow_flexion": 0.0,
            },
            description="Bar breaks the floor, knees extend.",
        ),
        Phase(
            name="clean_second_pull",
            time_fraction=0.25,
            joint_targets={
                "hip_flexion": math.radians(10),
                "knee_flexion": math.radians(-10),
                "shoulder_flexion": math.radians(40),
                "elbow_flexion": math.radians(20),
            },
            description="Explosive triple extension.",
        ),
        Phase(
            name="clean_catch",
            time_fraction=0.40,
            joint_targets={
                "hip_flexion": math.radians(100),
                "knee_flexion": math.radians(-100),
                "shoulder_flexion": math.radians(80),
                "elbow_flexion": math.radians(140),
            },
            description="Receiving bar in front rack, deep squat.",
        ),
        Phase(
            name="jerk_dip",
            time_fraction=0.55,
            joint_targets={
                "hip_flexion": math.radians(20),
                "knee_flexion": math.radians(-30),
                "shoulder_flexion": math.radians(80),
                "elbow_flexion": math.radians(140),
            },
            description="Dip before the jerk drive.",
        ),
        Phase(
            name="jerk_drive",
            time_fraction=0.70,
            joint_targets={
                "hip_flexion": math.radians(5),
                "knee_flexion": math.radians(-5),
                "shoulder_flexion": math.radians(150),
                "elbow_flexion": math.radians(30),
            },
            description="Explosive drive upward with leg and arm extension.",
        ),
        Phase(
            name="jerk_split",
            time_fraction=0.85,
            joint_targets={
                "hip_flexion": math.radians(30),
                "knee_flexion": math.radians(-40),
                "shoulder_flexion": math.radians(180),
                "elbow_flexion": 0.0,
            },
            description="Split position with bar locked out overhead.",
        ),
        Phase(
            name="jerk_recovery",
            time_fraction=1.0,
            joint_targets={
                "hip_flexion": 0.0,
                "knee_flexion": 0.0,
                "shoulder_flexion": math.radians(180),
                "elbow_flexion": 0.0,
            },
            description="Feet together, bar stable overhead.",
        ),
    ),
)
