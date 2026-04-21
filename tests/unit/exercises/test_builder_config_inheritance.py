"""Tests for shared exercise builder construction behavior.

Regression coverage for issues #169, #170, #171 which tracked regressions
introduced by PR #166:
- #169: CI workflow must not contain merge conflict markers
- #170: EXERCISE_BUILDERS must be exported from opensim_models.exercises
- #171: exercise model builder classes and build functions must be importable
"""

from __future__ import annotations

import pathlib

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.bench_press.bench_press_model import (
    BenchPressModelBuilder,
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    CleanAndJerkModelBuilder,
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import (
    DeadliftModelBuilder,
    build_deadlift_model,
)
from opensim_models.exercises.gait.gait_model import (
    GaitModelBuilder,
    build_gait_model,
)
from opensim_models.exercises.sit_to_stand.sit_to_stand_model import (
    SitToStandModelBuilder,
    build_sit_to_stand_model,
)
from opensim_models.exercises.snatch.snatch_model import (
    SnatchModelBuilder,
    build_snatch_model,
)
from opensim_models.exercises.squat.squat_model import (
    SquatModelBuilder,
    build_squat_model,
)
from opensim_models.shared.barbell import BarbellSpec
from opensim_models.shared.body import BodyModelSpec

_REPO_ROOT = pathlib.Path(__file__).parents[3]
_CI_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "ci-standard.yml"

_EXPECTED_KEYS = {
    "bench_press",
    "clean_and_jerk",
    "deadlift",
    "gait",
    "sit_to_stand",
    "snatch",
    "squat",
}

_EXPECTED_BUILD_FNS = [
    ("bench_press", build_bench_press_model),
    ("clean_and_jerk", build_clean_and_jerk_model),
    ("deadlift", build_deadlift_model),
    ("gait", build_gait_model),
    ("sit_to_stand", build_sit_to_stand_model),
    ("snatch", build_snatch_model),
    ("squat", build_squat_model),
]


# ---------------------------------------------------------------------------
# Issue #169 regression: CI workflow must be free of merge conflict markers
# ---------------------------------------------------------------------------


def test_ci_workflow_has_no_conflict_markers() -> None:
    """Regression for #169: ci-standard.yml must not contain conflict markers."""
    text = _CI_WORKFLOW.read_text(encoding="utf-8")
    conflict_markers = ("<<<<<<", "=======", ">>>>>>>")
    found = [m for m in conflict_markers if m in text]
    msg = f"Conflict markers found in ci-standard.yml: {found}"
    assert not found, msg


def test_ci_workflow_is_valid_yaml() -> None:
    """CI workflow file must be parseable as YAML."""
    import yaml  # noqa: PLC0415

    text = _CI_WORKFLOW.read_text(encoding="utf-8")
    result = yaml.safe_load(text)
    assert isinstance(result, dict), "ci-standard.yml parsed to unexpected type"
    assert "jobs" in result, "ci-standard.yml missing 'jobs' key"


# ---------------------------------------------------------------------------
# Issue #170 regression: EXERCISE_BUILDERS must be exported
# ---------------------------------------------------------------------------


def test_exercise_builders_dict_is_exported() -> None:
    """Regression for #170: EXERCISE_BUILDERS must be importable from exercises."""
    assert isinstance(EXERCISE_BUILDERS, dict), "EXERCISE_BUILDERS is not a dict"
    assert EXERCISE_BUILDERS, "EXERCISE_BUILDERS must not be empty"


def test_exercise_builders_has_all_expected_keys() -> None:
    """EXERCISE_BUILDERS must contain all seven exercise keys."""
    missing = _EXPECTED_KEYS - set(EXERCISE_BUILDERS.keys())
    msg = f"EXERCISE_BUILDERS missing keys: {missing}"
    assert not missing, msg


@pytest.mark.parametrize("key,expected_fn", _EXPECTED_BUILD_FNS)
def test_exercise_builders_values_are_correct_functions(
    key: str, expected_fn: object
) -> None:
    """Each EXERCISE_BUILDERS value must reference the canonical build function."""
    assert EXERCISE_BUILDERS[key] is expected_fn, (
        f"EXERCISE_BUILDERS[{key!r}] points to wrong callable"
    )


# ---------------------------------------------------------------------------
# Issue #171 regression: exercise model builder classes must be importable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "builder_cls",
    [
        BenchPressModelBuilder,
        CleanAndJerkModelBuilder,
        DeadliftModelBuilder,
        GaitModelBuilder,
        SitToStandModelBuilder,
        SnatchModelBuilder,
        SquatModelBuilder,
    ],
)
def test_exercise_builder_class_is_importable(builder_cls: type) -> None:
    """Regression for #171: every builder class must be importable (not empty)."""
    assert callable(builder_cls), f"{builder_cls} is not callable"
    assert hasattr(builder_cls, "build"), f"{builder_cls} missing .build() method"


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
def test_exercise_builders_inherit_base_constructor(builder_cls: type) -> None:
    config = ExerciseConfig(
        body_spec=BodyModelSpec(total_mass=82.0, height=1.8),
        barbell_spec=BarbellSpec.mens_olympic(plate_mass_per_side=35.0),
        grip_offset=0.33,
    )

    builder = builder_cls(config)

    assert builder.config is config
