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
