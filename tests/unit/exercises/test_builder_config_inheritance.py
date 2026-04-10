"""Tests for shared exercise builder construction behavior."""

import pytest

from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.bench_press.bench_press_model import (
    BenchPressModelBuilder,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    CleanAndJerkModelBuilder,
)
from opensim_models.exercises.deadlift.deadlift_model import DeadliftModelBuilder
from opensim_models.exercises.snatch.snatch_model import SnatchModelBuilder
from opensim_models.exercises.squat.squat_model import SquatModelBuilder
from opensim_models.shared.barbell import BarbellSpec
from opensim_models.shared.body import BodyModelSpec


@pytest.mark.parametrize(
    "builder_cls",
    [
        BenchPressModelBuilder,
        CleanAndJerkModelBuilder,
        DeadliftModelBuilder,
        SnatchModelBuilder,
        SquatModelBuilder,
    ],
)
def test_exercise_builders_inherit_base_constructor(builder_cls):
    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=82.0, height=1.8),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=35.0),
        grip_offset=0.33,
    )

    builder = builder_cls(config)

    assert builder.config is config
