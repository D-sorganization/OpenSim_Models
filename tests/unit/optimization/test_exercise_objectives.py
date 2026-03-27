"""Tests for exercise-specific optimization objectives and trajectory framework."""

from __future__ import annotations

import numpy as np
import pytest

from opensim_models.optimization.exercise_objectives import (
    EXERCISE_OBJECTIVES,
    ExerciseObjective,
    Phase,
    get_exercise_objective,
)
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
    TrajectoryResult,
    create_moco_study,
    interpolate_phases,
)

# ---------------------------------------------------------------------------
# All five objectives exist and are well-formed
# ---------------------------------------------------------------------------

EXPECTED_EXERCISES = {
    "squat",
    "deadlift",
    "bench_press",
    "snatch",
    "clean_and_jerk",
    "gait",
    "sit_to_stand",
}


class TestExerciseObjectiveRegistry:
    """Verify the registry contains all expected exercises."""

    def test_all_exercises_present(self) -> None:
        assert set(EXERCISE_OBJECTIVES.keys()) == EXPECTED_EXERCISES

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_get_exercise_objective_returns_correct_type(self, name: str) -> None:
        obj = get_exercise_objective(name)
        assert isinstance(obj, ExerciseObjective)
        assert obj.name == name

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_objective_has_at_least_two_phases(self, name: str) -> None:
        obj = get_exercise_objective(name)
        assert len(obj.phases) >= 2

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_phases_have_joint_targets(self, name: str) -> None:
        obj = get_exercise_objective(name)
        for phase in obj.phases:
            assert isinstance(phase.joint_targets, dict)

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_primary_coordinates_not_empty(self, name: str) -> None:
        obj = get_exercise_objective(name)
        assert len(obj.primary_coordinates) >= 1


class TestPhaseMonotonicity:
    """Phase time fractions must be strictly monotonically increasing."""

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_time_fractions_strictly_increasing(self, name: str) -> None:
        obj = get_exercise_objective(name)
        fractions = [p.time_fraction for p in obj.phases]
        for i in range(1, len(fractions)):
            assert fractions[i] > fractions[i - 1], (
                f"{name}: phase {i} fraction {fractions[i]} "
                f"<= phase {i - 1} fraction {fractions[i - 1]}"
            )

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_first_phase_starts_at_zero(self, name: str) -> None:
        obj = get_exercise_objective(name)
        assert obj.phases[0].time_fraction == 0.0

    @pytest.mark.parametrize("name", sorted(EXPECTED_EXERCISES))
    def test_last_phase_ends_at_one(self, name: str) -> None:
        obj = get_exercise_objective(name)
        assert obj.phases[-1].time_fraction == 1.0


class TestPhaseCount:
    """Verify expected number of phases per exercise."""

    @pytest.mark.parametrize(
        ("name", "expected_count"),
        [
            ("squat", 5),
            ("deadlift", 5),
            ("bench_press", 5),
            ("snatch", 6),
            ("clean_and_jerk", 8),
            ("gait", 8),
            ("sit_to_stand", 6),
        ],
    )
    def test_phase_count(self, name: str, expected_count: int) -> None:
        obj = get_exercise_objective(name)
        assert len(obj.phases) == expected_count


# ---------------------------------------------------------------------------
# Phase validation
# ---------------------------------------------------------------------------


class TestPhaseValidation:
    """Validation rules on individual Phase instances."""

    def test_phase_rejects_negative_time_fraction(self) -> None:
        with pytest.raises(ValueError, match="time_fraction"):
            Phase(name="bad", time_fraction=-0.1)

    def test_phase_rejects_time_fraction_above_one(self) -> None:
        with pytest.raises(ValueError, match="time_fraction"):
            Phase(name="bad", time_fraction=1.5)

    def test_exercise_objective_rejects_single_phase(self) -> None:
        with pytest.raises(ValueError, match="at least 2 phases"):
            ExerciseObjective(
                name="broken",
                phases=(Phase(name="only", time_fraction=0.0),),
            )

    def test_exercise_objective_rejects_non_monotonic(self) -> None:
        with pytest.raises(ValueError, match="monotonic"):
            ExerciseObjective(
                name="broken",
                phases=(
                    Phase(name="a", time_fraction=0.0),
                    Phase(name="b", time_fraction=0.5),
                    Phase(name="c", time_fraction=0.3),
                ),
            )


# ---------------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------------


class TestInterpolatePhases:
    """Test phase interpolation into dense keyframes."""

    def test_output_shape(self) -> None:
        obj = get_exercise_objective("squat")
        result = interpolate_phases(obj, num_points=50, duration=2.0)
        assert result.time.shape == (50,)
        for arr in result.coordinates.values():
            assert arr.shape == (50,)

    def test_time_range(self) -> None:
        obj = get_exercise_objective("deadlift")
        result = interpolate_phases(obj, num_points=100, duration=4.0)
        np.testing.assert_almost_equal(result.time[0], 0.0)
        np.testing.assert_almost_equal(result.time[-1], 4.0)

    def test_interpolation_endpoints_match_phases(self) -> None:
        obj = get_exercise_objective("squat")
        result = interpolate_phases(obj, num_points=200, duration=3.0)
        # First point should match first phase targets
        for coord, value in obj.phases[0].joint_targets.items():
            np.testing.assert_almost_equal(
                result.coordinates[coord][0], value, decimal=5
            )
        # Last point should match last phase targets
        for coord, value in obj.phases[-1].joint_targets.items():
            np.testing.assert_almost_equal(
                result.coordinates[coord][-1], value, decimal=5
            )

    def test_rejects_fewer_than_two_points(self) -> None:
        obj = get_exercise_objective("squat")
        with pytest.raises(ValueError, match="num_points"):
            interpolate_phases(obj, num_points=1)

    def test_rejects_non_positive_duration(self) -> None:
        obj = get_exercise_objective("squat")
        with pytest.raises(ValueError, match="duration"):
            interpolate_phases(obj, num_points=10, duration=0.0)


# ---------------------------------------------------------------------------
# TrajectoryConfig / TrajectoryResult
# ---------------------------------------------------------------------------


class TestTrajectoryDataclasses:
    """Test TrajectoryConfig and TrajectoryResult creation."""

    def test_config_defaults(self) -> None:
        cfg = TrajectoryConfig()
        assert cfg.exercise_name == "squat"
        assert cfg.duration == 3.0
        assert cfg.num_mesh_points == 50
        assert cfg.max_iterations == 1000

    def test_config_custom_values(self) -> None:
        cfg = TrajectoryConfig(
            exercise_name="deadlift",
            duration=5.0,
            num_mesh_points=100,
        )
        assert cfg.exercise_name == "deadlift"
        assert cfg.duration == 5.0
        assert cfg.num_mesh_points == 100

    def test_result_creation(self) -> None:
        result = TrajectoryResult(
            time=np.linspace(0, 1, 10),
            coordinates={"hip_flexion": np.zeros(10)},
            converged=True,
            objective_value=0.5,
            iterations=42,
        )
        assert result.converged is True
        assert result.iterations == 42
        assert result.time.shape == (10,)


# ---------------------------------------------------------------------------
# Moco study creation
# ---------------------------------------------------------------------------


class TestCreateMocoStudy:
    """Test the Moco study configuration builder."""

    def test_returns_dict_with_expected_keys(self) -> None:
        cfg = TrajectoryConfig(exercise_name="squat")
        study = create_moco_study(cfg)
        assert "solver" in study
        assert "problem" in study
        assert "initial_guess" in study

    def test_solver_params_match_config(self) -> None:
        cfg = TrajectoryConfig(max_iterations=500, convergence_tolerance=1e-6)
        study = create_moco_study(cfg)
        assert study["solver"]["max_iterations"] == 500
        assert study["solver"]["convergence_tolerance"] == 1e-6

    def test_initial_guess_has_time_and_coordinates(self) -> None:
        cfg = TrajectoryConfig(exercise_name="bench_press", num_mesh_points=25)
        study = create_moco_study(cfg)
        assert len(study["initial_guess"]["time"]) == 25
        assert len(study["initial_guess"]["coordinates"]) > 0

    def test_unknown_exercise_raises_key_error(self) -> None:
        cfg = TrajectoryConfig(exercise_name="curls_in_squat_rack")
        with pytest.raises(KeyError, match="curls_in_squat_rack"):
            create_moco_study(cfg)


# ---------------------------------------------------------------------------
# get_exercise_objective error handling
# ---------------------------------------------------------------------------


class TestGetExerciseObjectiveErrors:
    """Error handling for the lookup function."""

    def test_unknown_name_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown exercise"):
            get_exercise_objective("burpees")

    def test_error_message_lists_available(self) -> None:
        with pytest.raises(KeyError, match="squat"):
            get_exercise_objective("nonexistent")
