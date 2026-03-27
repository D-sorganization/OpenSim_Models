"""Cross-repo parity compliance tests.

Validates that the canonical biomechanical parameters match the
cross-repo parity standard shared across all fleet repositories.
"""

from __future__ import annotations

import math

import pytest

from opensim_models.shared.parity.standard import (
    EXERCISE_PHASE_COUNTS,
    FOOT_CONTACT_DIMS,
    GRAVITY,
    GROUND_FRICTION,
    JOINT_LIMITS,
    MENS_BARBELL,
    SEGMENT_LENGTH_FRACTIONS,
    SEGMENT_MASS_FRACTIONS,
    STANDARD_BODY_MASS,
    STANDARD_HEIGHT,
)


class TestAnthropometricDefaults:
    """Standard body defaults must match the parity spec."""

    def test_body_mass(self):
        assert STANDARD_BODY_MASS == 80.0

    def test_height(self):
        assert STANDARD_HEIGHT == 1.75


class TestSegmentMassFractions:
    """Segment mass fractions must sum to ~1.0 and contain required keys."""

    REQUIRED_SEGMENTS = {
        "pelvis",
        "torso",
        "head",
        "upper_arm",
        "forearm",
        "hand",
        "thigh",
        "shank",
        "foot",
    }

    def test_required_keys_present(self):
        assert set(SEGMENT_MASS_FRACTIONS) >= self.REQUIRED_SEGMENTS

    def test_fractions_sum_bilateral(self):
        """Bilateral sum: paired limbs counted twice."""
        paired = {"upper_arm", "forearm", "hand", "thigh", "shank", "foot"}
        total = sum(v * (2 if k in paired else 1) for k, v in SEGMENT_MASS_FRACTIONS.items())
        assert abs(total - 1.0) < 0.01

    def test_all_positive(self):
        for key, val in SEGMENT_MASS_FRACTIONS.items():
            assert val > 0, f"{key} mass fraction must be positive"


class TestSegmentLengthFractions:
    """Segment length fractions must contain required keys."""

    def test_required_keys_present(self):
        required = {
            "pelvis",
            "torso",
            "head",
            "upper_arm",
            "forearm",
            "hand",
            "thigh",
            "shank",
            "foot",
        }
        assert required <= set(SEGMENT_LENGTH_FRACTIONS)

    def test_all_positive(self):
        for key, val in SEGMENT_LENGTH_FRACTIONS.items():
            assert val > 0, f"{key} length fraction must be positive"


class TestJointLimits:
    """Joint limits must be in radians and satisfy lower < upper."""

    REQUIRED_JOINTS = {
        "hip_flex",
        "hip_adduct",
        "hip_rotate",
        "knee_flex",
        "ankle_flex",
        "ankle_invert",
        "shoulder_flex",
        "shoulder_adduct",
        "shoulder_rotate",
        "elbow_flex",
        "wrist_flex",
        "wrist_deviate",
        "lumbar_flex",
        "lumbar_lateral",
        "lumbar_rotate",
        "neck_flex",
    }

    def test_required_joints_present(self):
        assert set(JOINT_LIMITS) >= self.REQUIRED_JOINTS

    def test_lower_less_than_upper(self):
        for joint, (lo, hi) in JOINT_LIMITS.items():
            assert lo < hi, f"{joint}: lower {lo} >= upper {hi}"

    def test_values_in_radians(self):
        """All limits should be within plausible radian range."""
        for joint, (lo, hi) in JOINT_LIMITS.items():
            assert -math.pi <= lo <= math.pi, f"{joint} lower out of range"
            assert -math.pi <= hi <= math.pi, f"{joint} upper out of range"


class TestMensBarbell:
    """Men's Olympic barbell spec."""

    def test_bar_mass(self):
        assert MENS_BARBELL["bar_mass"] == 20.0

    def test_total_length(self):
        assert MENS_BARBELL["total_length"] == pytest.approx(2.20)

    def test_shaft_diameter(self):
        assert MENS_BARBELL["shaft_diameter"] == pytest.approx(0.028)


class TestFootContactDims:
    """Foot contact geometry."""

    def test_keys(self):
        assert {"length", "width", "height"} == set(FOOT_CONTACT_DIMS)

    def test_all_positive(self):
        for key, val in FOOT_CONTACT_DIMS.items():
            assert val > 0, f"{key} must be positive"


class TestGroundFriction:
    """Ground friction coefficients."""

    def test_static_greater_than_dynamic(self):
        assert GROUND_FRICTION["static"] > GROUND_FRICTION["dynamic"]

    def test_both_positive(self):
        assert GROUND_FRICTION["static"] > 0
        assert GROUND_FRICTION["dynamic"] > 0


class TestExercisePhaseCounts:
    """Exercise phase counts for supported lifts."""

    REQUIRED_EXERCISES = {
        "back_squat",
        "deadlift",
        "bench_press",
        "snatch",
        "clean_and_jerk",
    }

    def test_required_exercises_present(self):
        assert set(EXERCISE_PHASE_COUNTS) >= self.REQUIRED_EXERCISES

    def test_all_counts_positive(self):
        for ex, count in EXERCISE_PHASE_COUNTS.items():
            assert count > 0, f"{ex} phase count must be positive"
            assert isinstance(count, int), f"{ex} count must be int"


class TestGravity:
    """Gravity vector must point downward with standard magnitude."""

    def test_direction(self):
        assert GRAVITY[0] == 0.0
        assert GRAVITY[1] < 0.0
        assert GRAVITY[2] == 0.0

    def test_magnitude(self):
        mag = math.sqrt(sum(g**2 for g in GRAVITY))
        assert mag == pytest.approx(9.80665, abs=1e-4)
