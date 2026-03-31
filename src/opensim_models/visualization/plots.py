"""Professional visualization functions for biomechanical analysis.

Provides publication-quality plots for joint trajectories and exercise
phase diagrams using matplotlib with consistent styling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from matplotlib.figure import Figure

    from opensim_models.optimization.exercise_objectives import ExerciseObjective

logger = logging.getLogger(__name__)

# Professional style defaults
_STYLE = {
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def _validate_trajectory_inputs(
    time: np.ndarray,
    positions: dict[str, np.ndarray],
    joint_names: list[str],
) -> None:
    """Raise ValueError if any joint name or array length is invalid."""
    for name in joint_names:
        if name not in positions:
            raise ValueError(f"Joint '{name}' not found in positions dict")
        if len(positions[name]) != len(time):
            raise ValueError(
                f"Joint '{name}' has {len(positions[name])} values "
                f"but time has {len(time)} values"
            )


def _draw_trajectory_panels(
    time: np.ndarray,
    positions: dict[str, np.ndarray],
    joint_names: list[str],
    title: str,
) -> Figure:
    """Render one subplot per joint and return the Figure."""
    n_joints = len(joint_names)
    with plt.rc_context(_STYLE):
        fig, axes = plt.subplots(n_joints, 1, figsize=(10, 2.5 * n_joints), sharex=True)
        if n_joints == 1:
            axes = [axes]

        for ax, name in zip(axes, joint_names, strict=True):
            angles_deg = np.degrees(positions[name])
            ax.plot(time, angles_deg, linewidth=1.5, color="#2c7bb6")
            ax.set_ylabel(f"{name}\n(deg)")
            ax.legend([name], loc="upper right")

        axes[-1].set_xlabel("Time (s)")
        fig.suptitle(title, fontsize=14, fontweight="bold")
        fig.tight_layout()
    return fig


def plot_joint_trajectory(
    time: np.ndarray,
    positions: dict[str, np.ndarray],
    joint_names: list[str] | None = None,
    title: str = "Joint Angle Trajectories",
) -> Figure:
    """Create a multi-panel joint angle time series plot.

    Each joint gets its own subplot arranged vertically.

    Args:
        time: 1-D array of time values in seconds.
        positions: Mapping of joint name to 1-D array of angles (radians).
        joint_names: Subset of joints to plot. If None, plots all.
        title: Overall figure title.

    Returns:
        matplotlib Figure object.

    Raises:
        ValueError: If time and position arrays have mismatched lengths.
    """
    if joint_names is None:
        joint_names = sorted(positions.keys())

    if not joint_names:
        raise ValueError("No joints to plot: positions dict is empty")

    _validate_trajectory_inputs(time, positions, joint_names)
    fig = _draw_trajectory_panels(time, positions, joint_names, title)
    logger.info("Created joint trajectory plot with %d panels", len(joint_names))
    return fig


def _collect_phase_coords(objective: ExerciseObjective) -> list[str]:
    """Return sorted list of all coordinate names used across phases."""
    all_coords: set[str] = set()
    for phase in objective.phases:
        all_coords.update(phase.joint_targets.keys())
    return sorted(all_coords)


def _draw_coord_traces(
    ax: Any,
    objective: ExerciseObjective,
    coord_list: list[str],
    colors: Any,
) -> None:
    """Plot one trajectory line per coordinate on *ax*."""
    for idx, coord in enumerate(coord_list):
        t_vals = []
        angle_vals = []
        for phase in objective.phases:
            if coord in phase.joint_targets:
                t_vals.append(phase.time_fraction)
                angle_vals.append(np.degrees(phase.joint_targets[coord]))
        ax.plot(
            t_vals,
            angle_vals,
            marker="o",
            markersize=8,
            linewidth=2,
            color=colors[idx],
            label=coord,
        )


def _annotate_phase_names(ax: Any, objective: ExerciseObjective) -> None:
    """Draw vertical phase-boundary lines and rotated phase-name annotations."""
    for phase in objective.phases:
        ax.axvline(phase.time_fraction, color="gray", linestyle=":", alpha=0.4)
        ax.annotate(
            phase.name,
            xy=(phase.time_fraction, 1.02),
            xycoords=cast(Any, ("data", "axes fraction")),
            ha="center",
            va="bottom",
            fontsize=8,
            rotation=45,
        )


def plot_phase_diagram(
    objective: ExerciseObjective,
    title: str | None = None,
) -> Figure:
    """Create a visual phase progression diagram for an exercise.

    Shows phase waypoints as markers connected by lines, with phase names
    annotated. Each primary coordinate gets its own trace.

    Args:
        objective: ExerciseObjective with phases to visualize.
        title: Plot title. Defaults to the exercise name.

    Returns:
        matplotlib Figure object.
    """
    if title is None:
        title = f"{objective.name.replace('_', ' ').title()} Phase Diagram"

    coord_list = _collect_phase_coords(objective)
    if not coord_list:
        raise ValueError(f"Exercise '{objective.name}' has no joint targets in phases")

    cmap = matplotlib.colormaps["Set2"]
    colors = cmap(np.linspace(0, 1, max(len(coord_list), 1)))

    with plt.rc_context(_STYLE):
        fig, ax = plt.subplots(figsize=(12, 6))
        _draw_coord_traces(ax, objective, coord_list, colors)
        _annotate_phase_names(ax, objective)
        ax.set_xlabel("Normalised Time (0-1)")
        ax.set_ylabel("Joint Angle (deg)")
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="best", framealpha=0.9)
        fig.tight_layout()

    logger.info("Created phase diagram for '%s'", objective.name)
    return fig
