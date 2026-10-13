"""Data structures for tool execution results."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class InverseDynamicsResult:
    """Results from an inverse dynamics calculation.

    Attributes:
        forces_file: Path to the generated generalized forces .sto file.
        time: 1D array of time stamps for the solved trajectory.
        forces: Mapping from generalized force/moment names to 1D value arrays.
        column_labels: Complete list of column headers from the output file.
    """

    forces_file: Path
    time: np.ndarray
    forces: dict[str, np.ndarray]
    column_labels: list[str]

    def get_coordinate_force(self, coordinate_name: str) -> np.ndarray:
        """Return generalized force/moment for a named coordinate.

        Tries ``<coordinate_name>``, ``<coordinate_name>_force``, and
        ``<coordinate_name>_moment``.
        """
        for candidate in (
            coordinate_name,
            f"{coordinate_name}_force",
            f"{coordinate_name}_moment",
        ):
            if candidate in self.forces:
                return self.forces[candidate]
        raise KeyError(
            f"Coordinate force '{coordinate_name}' not found in results. "
            f"Available: {list(self.forces.keys())}"
        )


@dataclass(frozen=True)
class InverseKinematicsResult:
    """Results from an inverse kinematics calculation.

    Attributes:
        motion_file: Path to the generated motion .mot file.
        time: 1D array of time stamps for the solved trajectory.
        coordinates: Mapping from coordinate names to 1D value arrays
            (radians for rotational coordinates, meters for translational coordinates).
        column_labels: Complete list of column headers from the output file.
        in_degrees: Whether the raw motion file on disk was written in degrees.
    """

    motion_file: Path
    time: np.ndarray
    coordinates: dict[str, np.ndarray]
    column_labels: list[str]
    in_degrees: bool = True

    def get_coordinate_values(
        self, coordinate_name: str, *, in_degrees: bool = False
    ) -> np.ndarray:
        """Return values for a named coordinate.

        Args:
            coordinate_name: Name of the coordinate.
            in_degrees: If True, convert radian values to degrees.
        """
        if coordinate_name in self.coordinates:
            vals = self.coordinates[coordinate_name]
            return np.rad2deg(vals) if in_degrees else vals
        raise KeyError(
            f"Coordinate '{coordinate_name}' not found in results. "
            f"Available: {list(self.coordinates.keys())}"
        )

    def get_coordinate_value(
        self, coordinate_name: str, *, in_degrees: bool = False
    ) -> np.ndarray:
        """Alias for get_coordinate_values."""
        return self.get_coordinate_values(coordinate_name, in_degrees=in_degrees)
