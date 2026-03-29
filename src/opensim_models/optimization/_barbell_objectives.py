"""Objective definitions for barbell exercises (squat, deadlift, bench press)."""

from __future__ import annotations

import math

from opensim_models.optimization._types import ExerciseObjective, Phase

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
