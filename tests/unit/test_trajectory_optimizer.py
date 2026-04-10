"""Dedicated tests for trajectory optimization helpers."""

from __future__ import annotations

import numpy as np
import pytest

from opensim_models.optimization._types import ExerciseObjective, Phase
from opensim_models.optimization.trajectory_optimizer import (
    TrajectoryConfig,
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
        assert cfg.duration == 4.5
        assert cfg.num_mesh_points == 75
        assert cfg.max_iterations == 250
        assert cfg.convergence_tolerance == 1e-5
        assert cfg.constraint_tolerance == 2e-5
        assert cfg.weight_tracking == 12.0
        assert cfg.weight_effort == 0.25


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
            (4, 0.0, "duration"),
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
