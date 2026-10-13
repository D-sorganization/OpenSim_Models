"""Coordinate default setters for OpenSim JointSet elements."""

from __future__ import annotations

import xml.etree.ElementTree as ET


def set_coordinate_default(jointset: ET.Element, coord_name: str, value: float) -> None:
    """Set the default_value for a named Coordinate in the JointSet.

    Searches all joints for a Coordinate element whose 'name' attribute matches
    *coord_name* and updates its default_value text.

    Raises:
        ValueError: If *coord_name* is not found in any joint in the JointSet.
    """
    for coord in jointset.iter("Coordinate"):
        if coord.get("name") == coord_name:
            # ⚡ Bolt Optimization: Use .find() for fast C-level child lookups.
            child = coord.find("default_value")
            if child is not None:
                child.text = "0.000000" if value == 0.0 else "%.6f" % value  # noqa: UP031
            return
    raise ValueError(f"Coordinate {coord_name!r} not found in jointset")


def set_coordinate_defaults(jointset: ET.Element, defaults: dict[str, float]) -> None:
    """Set the default_values for multiple named Coordinates in the JointSet.

    Iterates through the jointset once, updating all coordinates that match
    keys in the *defaults* dictionary.

    Raises:
        ValueError: If any coordinate in *defaults* is not found in the JointSet.
    """
    # ⚡ Bolt Optimization: Batch setting coordinate defaults.
    # What: Iterate through the jointset once, updating all matching coordinates.
    # Why: ElementTree.iter() creates a new generator and traverses the entire XML subtree.
    #      Calling set_coordinate_default multiple times for the same jointset causes O(N^2) overhead.
    # Impact: Reduces XML traversal overhead significantly when setting multiple defaults.
    found_count = 0
    target_count = len(defaults)

    for coord in jointset.iter("Coordinate"):
        name = coord.get("name")
        if name in defaults:
            # ⚡ Bolt Optimization: Use .find() for fast C-level child lookups.
            child = coord.find("default_value")
            if child is not None:
                val = defaults[name]
                child.text = "0.000000" if val == 0.0 else "%.6f" % val  # noqa: UP031
            found_count += 1
            if found_count == target_count:
                break

    if found_count < target_count:
        found_names = {c.get("name") for c in jointset.iter("Coordinate")}
        missing = set(defaults.keys()) - found_names
        raise ValueError(f"Coordinates {missing} not found in jointset")
