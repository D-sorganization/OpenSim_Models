"""Shared biomechanical constants for barbell exercise models.

Floor-pull exercises (deadlift, snatch, clean-and-jerk) all start with the
bar on the floor and share the same approximate initial joint angles.
"""

from __future__ import annotations

# Initial joint angles for floor-pull exercises (bar starting on the ground).
# Values match standard competitive starting positions.
_FLOOR_PULL_HIP_ANGLE: float = 1.3963  # ~80° hip flexion
_FLOOR_PULL_KNEE_ANGLE: float = -1.0472  # ~60° knee flexion (negative convention)
_FLOOR_PULL_LUMBAR_ANGLE: float = 0.5236  # ~30° lumbar flexion

# Grip offsets from shaft centre (metres) for each exercise.
_SNATCH_GRIP_HALF_WIDTH: float = 0.58  # Wide snatch grip (~1.5× shoulder width)
_CLEAN_GRIP_HALF_WIDTH: float = 0.25  # Shoulder-width clean grip
