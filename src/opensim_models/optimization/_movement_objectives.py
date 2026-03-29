"""Objective definitions for non-barbell movement patterns (gait, sit-to-stand)."""

from __future__ import annotations

import math

from opensim_models.optimization._types import ExerciseObjective, Phase

GAIT = ExerciseObjective(
    name="gait",
    description="Walking gait cycle: heel strike through toe-off and swing.",
    primary_coordinates=("hip_flexion", "knee_flexion", "ankle_flexion"),
    phases=(
        Phase(
            name="heel_strike",
            time_fraction=0.0,
            joint_targets={
                "hip_flexion": math.radians(30),
                "knee_flexion": math.radians(-5),
                "ankle_flexion": math.radians(0),
            },
            description="Initial contact: heel strikes the ground.",
        ),
        Phase(
            name="loading_response",
            time_fraction=0.10,
            joint_targets={
                "hip_flexion": math.radians(25),
                "knee_flexion": math.radians(-15),
                "ankle_flexion": math.radians(-5),
            },
            description="Weight acceptance onto stance limb.",
        ),
        Phase(
            name="midstance",
            time_fraction=0.30,
            joint_targets={
                "hip_flexion": math.radians(0),
                "knee_flexion": math.radians(-5),
                "ankle_flexion": math.radians(10),
            },
            description="Single-limb support, body advancing over foot.",
        ),
        Phase(
            name="terminal_stance",
            time_fraction=0.50,
            joint_targets={
                "hip_flexion": math.radians(-10),
                "knee_flexion": math.radians(-5),
                "ankle_flexion": math.radians(15),
            },
            description="Heel rises, body moves ahead of the foot.",
        ),
        Phase(
            name="pre_swing",
            time_fraction=0.60,
            joint_targets={
                "hip_flexion": math.radians(0),
                "knee_flexion": math.radians(-35),
                "ankle_flexion": math.radians(-15),
            },
            description="Toe-off: rapid knee flexion, ankle plantarflexion.",
        ),
        Phase(
            name="initial_swing",
            time_fraction=0.73,
            joint_targets={
                "hip_flexion": math.radians(15),
                "knee_flexion": math.radians(-60),
                "ankle_flexion": math.radians(-5),
            },
            description="Foot clearance through hip and knee flexion.",
        ),
        Phase(
            name="mid_swing",
            time_fraction=0.87,
            joint_targets={
                "hip_flexion": math.radians(25),
                "knee_flexion": math.radians(-25),
                "ankle_flexion": math.radians(0),
            },
            description="Limb advances, knee begins extending.",
        ),
        Phase(
            name="terminal_swing",
            time_fraction=1.0,
            joint_targets={
                "hip_flexion": math.radians(30),
                "knee_flexion": math.radians(-5),
                "ankle_flexion": math.radians(0),
            },
            description="Knee extends, preparing for next heel strike.",
        ),
    ),
)

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
