"""Exercise-specific optimization objectives for OpenSim Moco trajectory planning.

Each exercise is described as a sequence of phases with target joint angles,
timing fractions, and coordinate bounds. These objectives drive the trajectory
optimizer to produce biomechanically realistic motion.

Design by Contract: all angle values are stored in radians internally.
Phases must have strictly monotonic time fractions in [0, 1].
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Phase:
    """A single phase within an exercise movement pattern.

    Attributes:
        name: Human-readable phase label (e.g. "bottom", "lockout").
        time_fraction: Normalised time within [0, 1] at which this phase occurs.
        joint_targets: Mapping of coordinate name to target angle in radians.
        description: Optional narrative description of the phase.
    """

    name: str
    time_fraction: float
    joint_targets: dict[str, float] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.time_fraction <= 1.0:
            raise ValueError(
                f"Phase '{self.name}' time_fraction must be in [0, 1], "
                f"got {self.time_fraction}"
            )


@dataclass(frozen=True)
class ExerciseObjective:
    """Complete movement objective for an exercise.

    Attributes:
        name: Canonical exercise name (e.g. "squat").
        phases: Ordered sequence of movement phases.
        primary_coordinates: Coordinate names most relevant to the exercise.
        description: Narrative summary of the movement.
    """

    name: str
    phases: tuple[Phase, ...]
    primary_coordinates: tuple[str, ...] = ()
    description: str = ""

    def __post_init__(self) -> None:
        if len(self.phases) < 2:
            raise ValueError(
                f"Exercise '{self.name}' must have at least 2 phases, "
                f"got {len(self.phases)}"
            )
        fractions = [p.time_fraction for p in self.phases]
        for i in range(1, len(fractions)):
            if fractions[i] <= fractions[i - 1]:
                raise ValueError(
                    f"Exercise '{self.name}' phases must have strictly monotonic "
                    f"time fractions. Phase '{self.phases[i].name}' "
                    f"({fractions[i]}) <= '{self.phases[i - 1].name}' "
                    f"({fractions[i - 1]})"
                )


# ---------------------------------------------------------------------------
# Exercise objective definitions
# ---------------------------------------------------------------------------

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
        # --- Clean ---
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
        # --- Jerk ---
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

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

EXERCISE_OBJECTIVES: dict[str, ExerciseObjective] = {
    "squat": SQUAT,
    "deadlift": DEADLIFT,
    "bench_press": BENCH_PRESS,
    "snatch": SNATCH,
    "clean_and_jerk": CLEAN_AND_JERK,
    "gait": GAIT,
    "sit_to_stand": SIT_TO_STAND,
}


def get_exercise_objective(name: str) -> ExerciseObjective:
    """Look up an exercise objective by canonical name.

    Raises:
        KeyError: If *name* is not a registered exercise.
    """
    try:
        return EXERCISE_OBJECTIVES[name]
    except KeyError:
        available = ", ".join(sorted(EXERCISE_OBJECTIVES))
        raise KeyError(f"Unknown exercise '{name}'. Available: {available}") from None
