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

# Multi-DOF joint defaults for floor-pull exercises.
_FLOOR_PULL_HIP_ADDUCT: float = 0.0  # neutral adduction
_FLOOR_PULL_HIP_ROTATE: float = 0.0  # neutral rotation

# Shoulder multi-DOF defaults.
_SHOULDER_NEUTRAL_ADDUCT: float = 0.0  # neutral adduction
_SHOULDER_NEUTRAL_ROTATE: float = 0.0  # neutral rotation

# Lumbar multi-DOF defaults.
_LUMBAR_NEUTRAL_LATERAL: float = 0.0  # neutral lateral flexion
_LUMBAR_NEUTRAL_ROTATE: float = 0.0  # neutral rotation

# Ankle multi-DOF defaults.
_ANKLE_NEUTRAL_INVERSION: float = 0.0  # neutral inversion/eversion

# Wrist multi-DOF defaults.
_WRIST_NEUTRAL_DEVIATION: float = 0.0  # neutral radial/ulnar deviation

# Squat-specific multi-DOF angles.
_SQUAT_HIP_EXTERNAL_ROTATE: float = 0.1745  # ~10° external rotation

# Bench press-specific multi-DOF angles.
_BENCH_SHOULDER_ADDUCT: float = -0.5236  # ~-30° (abducted from midline)

# Snatch-specific multi-DOF angles.
_SNATCH_SHOULDER_ABDUCT: float = -0.3491  # ~-20° abduction for wide grip

# Grip offsets from shaft centre (metres) for each exercise.
_SNATCH_GRIP_HALF_WIDTH: float = 0.58  # Wide snatch grip (~1.5× shoulder width)
_CLEAN_GRIP_HALF_WIDTH: float = 0.25  # Shoulder-width clean grip
