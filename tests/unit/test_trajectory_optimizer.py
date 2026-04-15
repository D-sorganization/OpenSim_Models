"""Dedicated tests for trajectory optimization helpers."""

from __future__ import annotations

import numpy as np
import pytest

from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
    TrajectoryResult,
    create_moco_study,
    interpolate_phases,
)


class TestTrajectoryConfigValidation:
    """TrajectoryConfig should enforce its contract at construction time."""

    @pytest.mark.parametrize(
        ("field_name", "value", "match"),
        [
            ("duration", 0.0, "duration"),
            ("num_mesh_points", 0, "num_mesh_points"),
            ("max_iterations", 0, "max_iterations"),
            ("convergence_tolerance", 0.0, "convergence_tolerance"),
            ("constraint_tolerance", 0.0, "constraint_tolerance"),
            ("weight_tracking", -1.0, "weight_tracking"),
            ("weight_effort", -0.1, "weight_effort"),
        ],
    )
    def test_rejects_invalid_values(
        self, field_name: str, value: float | int, match: str
    ) -> None:
        kwargs = {field_name: value}
        with pytest.raises(ValueError, match=match):
            TrajectoryConfig(**kwargs)

    def test_accepts_valid_custom_values(self) -> None:
        cfg = TrajectoryConfig(
            exercise_name="bench_press",
            duration=4.5,
            num_mesh_points=75,
            max_iterations=250,
            convergence_tolerance=1e-5,
            constraint_tolerance=2e-5,
            weight_tracking=12.0,
            weight_effort=0.25,
        )

        assert cfg.exercise_name == "bench_press"
        assert cfg.duration == pytest.approx(4.5)
        assert cfg.num_mesh_points == 75
        assert cfg.max_iterations == 250
        assert cfg.convergence_tolerance == pytest.approx(1e-5)
        assert cfg.constraint_tolerance == pytest.approx(2e-5)
        assert cfg.weight_tracking == pytest.approx(12.0)
        assert cfg.weight_effort == pytest.approx(0.25)

    def test_defaults_are_valid(self) -> None:
        """Default construction should succeed and produce expected defaults."""
        cfg = TrajectoryConfig()

        assert cfg.exercise_name == "squat"
        assert cfg.duration == pytest.approx(3.0)
        assert cfg.num_mesh_points == 50
        assert cfg.max_iterations == 1000
        assert cfg.convergence_tolerance == pytest.approx(1e-4)
        assert cfg.constraint_tolerance == pytest.approx(1e-4)
        assert cfg.weight_tracking == pytest.approx(10.0)
        assert cfg.weight_effort == pytest.approx(1.0)

    def test_zero_weights_are_allowed(self) -> None:
        """Non-negative weights permit zero (disabling a cost term)."""
        cfg = TrajectoryConfig(weight_tracking=0.0, weight_effort=0.0)

        assert cfg.weight_tracking == pytest.approx(0.0)
        assert cfg.weight_effort == pytest.approx(0.0)


class TestInterpolatePhases:
    """Interpolation should preserve phase endpoints and fill sparse targets."""

    def test_interpolates_sparse_coordinate_as_constant(self) -> None:
        objective = ExerciseObjective(
            name="custom",
            phases=(
                Phase(
                    name="start",
                    time_fraction=0.0,
                    joint_targets={"hip_flexion": 1.0, "knee_flexion": 0.2},
                ),
                Phase(
                    name="finish",
                    time_fraction=1.0,
                    joint_targets={"knee_flexion": 0.8},
                ),
            ),
        )

        result = interpolate_phases(objective, num_points=5, duration=2.0)

        np.testing.assert_allclose(result.time, np.linspace(0.0, 2.0, 5))
        np.testing.assert_allclose(result.coordinates["hip_flexion"], 1.0)
        np.testing.assert_allclose(
            result.coordinates["knee_flexion"],
            np.linspace(0.2, 0.8, 5),
        )

    @pytest.mark.parametrize(
        ("num_points", "duration", "match"),
        [
            (1, 1.0, "num_points"),
            (0, 1.0, "num_points"),
            (-3, 1.0, "num_points"),
            (4, 0.0, "duration"),
            (4, -0.5, "duration"),
            (4, float("nan"), "non-finite"),
            (4, float("inf"), "non-finite"),
            (4, float("-inf"), "non-finite"),
        ],
    )
    def test_rejects_invalid_sampling_arguments(
        self, num_points: int, duration: float, match: str
    ) -> None:
        objective = ExerciseObjective(
            name="custom",
            phases=(
                Phase(name="start", time_fraction=0.0),
                Phase(name="end", time_fraction=1.0),
            ),
        )

        with pytest.raises(ValueError, match=match):
            interpolate_phases(objective, num_points=num_points, duration=duration)

    def test_minimum_two_points_preserves_endpoints(self) -> None:
        """Boundary: num_points=2 should return exact start and end values."""
        objective = ExerciseObjective(
            name="custom",
            phases=(
                Phase(
                    name="start",
                    time_fraction=0.0,
                    joint_targets={"hip_flexion": 0.0},
                ),
                Phase(
                    name="end",
                    time_fraction=1.0,
                    joint_targets={"hip_flexion": 1.5},
                ),
            ),
        )

        result = interpolate_phases(objective, num_points=2, duration=1.0)

        assert result.time.shape == (2,)
        assert result.coordinates["hip_flexion"][0] == pytest.approx(0.0)
        assert result.coordinates["hip_flexion"][1] == pytest.approx(1.5)

    def test_intermediate_phase_is_hit_exactly(self) -> None:
        """A phase at t=0.5 with odd num_points must be sampled exactly."""
        objective = ExerciseObjective(
            name="custom",
            phases=(
                Phase(
                    name="start",
                    time_fraction=0.0,
                    joint_targets={"knee_flexion": 0.0},
                ),
                Phase(
                    name="mid",
                    time_fraction=0.5,
                    joint_targets={"knee_flexion": 2.0},
                ),
                Phase(
                    name="end",
                    time_fraction=1.0,
                    joint_targets={"knee_flexion": 0.0},
                ),
            ),
        )

        result = interpolate_phases(objective, num_points=5, duration=2.0)

        # Midpoint index == 2 for 5 evenly spaced samples.
        assert result.coordinates["knee_flexion"][2] == pytest.approx(2.0)
        assert result.coordinates["knee_flexion"][0] == pytest.approx(0.0)
        assert result.coordinates["knee_flexion"][-1] == pytest.approx(0.0)

    def test_result_reports_trivial_convergence(self) -> None:
        """Interpolated trajectories are tagged as converged with zero objective."""
        objective = ExerciseObjective(
            name="custom",
            phases=(
                Phase(
                    name="start",
                    time_fraction=0.0,
                    joint_targets={"hip_flexion": 0.0},
                ),
                Phase(
                    name="end",
                    time_fraction=1.0,
                    joint_targets={"hip_flexion": 1.0},
                ),
            ),
        )

        result = interpolate_phases(objective, num_points=3, duration=1.0)

        assert isinstance(result, TrajectoryResult)
        assert result.converged is True
        assert result.objective_value == pytest.approx(0.0)
        assert result.iterations == 0


class TestCreateMocoStudy:
    """The Moco study dict should reflect the supplied configuration."""

    def test_builds_solver_problem_and_initial_guess(self) -> None:
        cfg = TrajectoryConfig(
            exercise_name="squat",
            duration=2.5,
            num_mesh_points=12,
            max_iterations=222,
            convergence_tolerance=3e-5,
            constraint_tolerance=4e-5,
            weight_tracking=8.0,
            weight_effort=1.5,
        )

        study = create_moco_study(cfg)

        assert study["solver"] == {
            "type": "MocoCasADiSolver",
            "max_iterations": 222,
            "convergence_tolerance": 3e-5,
            "constraint_tolerance": 4e-5,
            "num_mesh_intervals": 12,
        }
        assert study["problem"]["exercise"] == "squat"
        assert study["problem"]["duration"] == 2.5
        assert study["problem"]["cost_weights"] == {
            "tracking": 8.0,
            "effort": 1.5,
        }
        assert len(study["initial_guess"]["time"]) == 12
        assert len(study["initial_guess"]["coordinates"]) > 0
        assert list(study["problem"]["coordinates"]) == list(
            study["initial_guess"]["coordinates"].keys()
        )

    def test_unknown_exercise_raises_key_error(self) -> None:
        """create_moco_study should propagate KeyError for unknown exercises."""
        cfg = TrajectoryConfig(exercise_name="definitely_not_an_exercise")

        with pytest.raises(KeyError, match="definitely_not_an_exercise"):
            create_moco_study(cfg)

    def test_initial_guess_time_starts_at_zero_and_ends_at_duration(self) -> None:
        """Initial guess time axis must span [0, duration]."""
        cfg = TrajectoryConfig(
            exercise_name="squat",
            duration=2.0,
            num_mesh_points=5,
        )

        study = create_moco_study(cfg)

        times = study["initial_guess"]["time"]
        assert times[0] == pytest.approx(0.0)
        assert times[-1] == pytest.approx(2.0)
        assert len(times) == 5
