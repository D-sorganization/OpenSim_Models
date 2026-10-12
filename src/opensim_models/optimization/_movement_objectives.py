"""Objective definitions for non-barbell movement patterns (gait, sit-to-stand).

Phases, time fractions (t_frac) and descriptions are consumed from the vendored
model-parity standard v2.0/v2.1 spec (Repository_Management#2060, RM#2025).
"""

from __future__ import annotations

import math
from typing import Any

from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.shared.parity._canonical import spec
from opensim_models.shared.parity.standard import STANDARD

_GAIT_TARGETS: dict[str, dict[str, float]] = {
    "initial_contact": {
        "hip_flexion": math.radians(30),
        "knee_flexion": math.radians(-5),
        "ankle_flexion": math.radians(0),
    },
    "loading_response": {
        "hip_flexion": math.radians(25),
        "knee_flexion": math.radians(-15),
        "ankle_flexion": math.radians(-5),
    },
    "mid_stance": {
        "hip_flexion": math.radians(0),
        "knee_flexion": math.radians(-5),
        "ankle_flexion": math.radians(10),
    },
    "terminal_stance": {
        "hip_flexion": math.radians(-10),
        "knee_flexion": math.radians(-5),
        "ankle_flexion": math.radians(15),
    },
    "pre_swing": {
        "hip_flexion": math.radians(0),
        "knee_flexion": math.radians(-35),
        "ankle_flexion": math.radians(-15),
    },
    "initial_swing": {
        "hip_flexion": math.radians(15),
        "knee_flexion": math.radians(-60),
        "ankle_flexion": math.radians(-5),
    },
    "mid_swing": {
        "hip_flexion": math.radians(25),
        "knee_flexion": math.radians(-25),
        "ankle_flexion": math.radians(0),
    },
    "terminal_swing": {
        "hip_flexion": math.radians(30),
        "knee_flexion": math.radians(-5),
        "ankle_flexion": math.radians(0),
    },
}

_SIT_TO_STAND_TARGETS: dict[str, dict[str, float]] = {
    "seated": {
        "hip_flexion": math.radians(90),
        "knee_flexion": math.radians(-90),
        "ankle_flexion": math.radians(10),
    },
    "trunk_flexion": {
        "hip_flexion": math.radians(110),
        "knee_flexion": math.radians(-90),
        "ankle_flexion": math.radians(15),
    },
    "seat_off": {
        "hip_flexion": math.radians(90),
        "knee_flexion": math.radians(-75),
        "ankle_flexion": math.radians(20),
    },
    "rising": {
        "hip_flexion": math.radians(45),
        "knee_flexion": math.radians(-40),
        "ankle_flexion": math.radians(10),
    },
    "extension_end": {
        "hip_flexion": math.radians(10),
        "knee_flexion": math.radians(-10),
        "ankle_flexion": math.radians(5),
    },
    "stabilisation": {
        "hip_flexion": math.radians(0),
        "knee_flexion": math.radians(0),
        "ankle_flexion": math.radians(0),
    },
}


def _build_phases(
    exercise: str, targets: dict[str, dict[str, float]]
) -> tuple[Phase, ...]:
    """Construct phases from the standard spec, populated with local targets."""
    spec_phases: list[dict[str, Any]] = spec.exercise_spec(STANDARD, exercise)["phases"]
    return tuple(
        Phase(
            name=str(p["name"]),
            time_fraction=float(p["t_frac"]),
            joint_targets=targets[str(p["name"])],
            description=str(p["definition"]),
        )
        for p in spec_phases
    )


GAIT = ExerciseObjective(
    name="gait",
    description="Walking gait cycle: heel strike through toe-off and swing.",
    primary_coordinates=("hip_flexion", "knee_flexion", "ankle_flexion"),
    phases=_build_phases("gait", _GAIT_TARGETS),
)

SIT_TO_STAND = ExerciseObjective(
    name="sit_to_stand",
    description="Sit-to-stand transfer from chair to upright standing.",
    primary_coordinates=("hip_flexion", "knee_flexion", "ankle_flexion"),
    phases=_build_phases("sit_to_stand", _SIT_TO_STAND_TARGETS),
)
