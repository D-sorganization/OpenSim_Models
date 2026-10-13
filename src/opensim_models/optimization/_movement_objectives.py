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

_HIP_KNEE_ANKLE = (
    "hip_l_flex",
    "hip_r_flex",
    "knee_l_flex",
    "knee_r_flex",
    "ankle_l_flex",
    "ankle_r_flex",
)


def _bilateral(hip: float, knee: float, ankle: float) -> dict[str, float]:
    return {
        "hip_l_flex": hip,
        "hip_r_flex": hip,
        "knee_l_flex": knee,
        "knee_r_flex": knee,
        "ankle_l_flex": ankle,
        "ankle_r_flex": ankle,
    }


_GAIT_TARGETS: dict[str, dict[str, float]] = {
    "initial_contact": _bilateral(
        hip=math.radians(30),
        knee=math.radians(-5),
        ankle=math.radians(0),
    ),
    "loading_response": _bilateral(
        hip=math.radians(25),
        knee=math.radians(-15),
        ankle=math.radians(-5),
    ),
    "mid_stance": _bilateral(
        hip=math.radians(0),
        knee=math.radians(-5),
        ankle=math.radians(10),
    ),
    "terminal_stance": _bilateral(
        hip=math.radians(-10),
        knee=math.radians(-5),
        ankle=math.radians(15),
    ),
    "pre_swing": _bilateral(
        hip=math.radians(0),
        knee=math.radians(-35),
        ankle=math.radians(-15),
    ),
    "initial_swing": _bilateral(
        hip=math.radians(15),
        knee=math.radians(-60),
        ankle=math.radians(-5),
    ),
    "mid_swing": _bilateral(
        hip=math.radians(25),
        knee=math.radians(-25),
        ankle=math.radians(0),
    ),
    "terminal_swing": _bilateral(
        hip=math.radians(30),
        knee=math.radians(-5),
        ankle=math.radians(0),
    ),
}

_SIT_TO_STAND_TARGETS: dict[str, dict[str, float]] = {
    "seated": _bilateral(
        hip=math.radians(90),
        knee=math.radians(-90),
        ankle=math.radians(10),
    ),
    "trunk_flexion": _bilateral(
        hip=math.radians(110),
        knee=math.radians(-90),
        ankle=math.radians(15),
    ),
    "seat_off": _bilateral(
        hip=math.radians(90),
        knee=math.radians(-75),
        ankle=math.radians(20),
    ),
    "rising": _bilateral(
        hip=math.radians(45),
        knee=math.radians(-40),
        ankle=math.radians(10),
    ),
    "extension_end": _bilateral(
        hip=math.radians(10),
        knee=math.radians(-10),
        ankle=math.radians(5),
    ),
    "stabilisation": _bilateral(
        hip=math.radians(0),
        knee=math.radians(0),
        ankle=math.radians(0),
    ),
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
    primary_coordinates=_HIP_KNEE_ANKLE,
    phases=_build_phases("gait", _GAIT_TARGETS),
)

SIT_TO_STAND = ExerciseObjective(
    name="sit_to_stand",
    description="Sit-to-stand transfer from chair to upright standing.",
    primary_coordinates=_HIP_KNEE_ANKLE,
    phases=_build_phases("sit_to_stand", _SIT_TO_STAND_TARGETS),
)
