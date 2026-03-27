"""Tests for visualization plots."""

from __future__ import annotations

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")  # Non-interactive backend for testing

from opensim_models.optimization.exercise_objectives import get_exercise_objective
from opensim_models.visualization.plots import plot_joint_trajectory, plot_phase_diagram


class TestPlotJointTrajectory:
    def test_returns_figure(self):
        time = np.linspace(0, 3, 100)
        positions = {
            "hip_flexion": np.sin(time),
            "knee_flexion": np.cos(time),
        }
        fig = plot_joint_trajectory(time, positions)
        assert fig is not None
        assert len(fig.axes) == 2

    def test_subset_of_joints(self):
        time = np.linspace(0, 3, 50)
        positions = {
            "hip_flexion": np.zeros(50),
            "knee_flexion": np.zeros(50),
            "ankle_flexion": np.zeros(50),
        }
        fig = plot_joint_trajectory(time, positions, joint_names=["hip_flexion"])
        assert len(fig.axes) == 1

    def test_raises_on_empty_positions(self):
        time = np.linspace(0, 3, 50)
        with pytest.raises(ValueError, match="No joints"):
            plot_joint_trajectory(time, {})

    def test_raises_on_mismatched_lengths(self):
        time = np.linspace(0, 3, 50)
        positions = {"hip_flexion": np.zeros(30)}
        with pytest.raises(ValueError, match="values"):
            plot_joint_trajectory(time, positions)

    def test_raises_on_missing_joint(self):
        time = np.linspace(0, 3, 50)
        positions = {"hip_flexion": np.zeros(50)}
        with pytest.raises(ValueError, match="not found"):
            plot_joint_trajectory(time, positions, joint_names=["nonexistent"])


class TestPlotPhaseDiagram:
    def test_returns_figure_for_squat(self):
        obj = get_exercise_objective("squat")
        fig = plot_phase_diagram(obj)
        assert fig is not None

    def test_returns_figure_for_gait(self):
        obj = get_exercise_objective("gait")
        fig = plot_phase_diagram(obj)
        assert fig is not None

    def test_returns_figure_for_sit_to_stand(self):
        obj = get_exercise_objective("sit_to_stand")
        fig = plot_phase_diagram(obj)
        assert fig is not None

    def test_custom_title(self):
        obj = get_exercise_objective("deadlift")
        fig = plot_phase_diagram(obj, title="Custom Title")
        assert fig is not None
