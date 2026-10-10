"""Tests for shoulder-abduction grip geometry (#394, #424)."""

from __future__ import annotations

import pytest

from opensim_models.exercises.constants import (
    _CLEAN_GRIP_HALF_WIDTH,
    _SNATCH_GRIP_HALF_WIDTH,
)
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.body.arm_geometry import shoulder_adduct_for_grip
from opensim_models.shared.body.body_model import WRIST_DEVIATION_RANGE


class TestShoulderAdductForGripRespectsWristCancellationRange:
    """``shoulder_adduct_for_grip`` must clamp its angle so that the
    wrist's *exact* counter-rotation (``-shoulder_adduct``) that keeps the
    bar level stays within the wrist's own declared range (#424).

    OpenSim's barbell-to-hand attachment rigidly ties both hands'
    orientation to the single shaft (a zero-DOF ``WeldJoint`` on the left,
    a ``WeldConstraint`` on the right), so this is not optional: clamping
    the wrist counter-rotation independently (leaving the shoulder at an
    angle the wrist cannot fully cancel) was confirmed with real-OpenSim
    forward kinematics to make ``initSystem()`` silently redistribute the
    mismatch across both wrists at assembly time, moving them off their
    declared defaults.
    """

    def test_wide_grip_is_clamped_by_the_wrist_cancellation_range(self) -> None:
        """The snatch's 0.58 m grip would need ~45.16 deg of shoulder
        abduction to reach exactly, which the wrist's own +30 deg bound
        cannot fully cancel -- so the achieved angle is bounded by the
        wrist, not just the shoulder's own (much larger) range."""
        spec = BodyModelSpec()
        theta, feasible = shoulder_adduct_for_grip(spec, _SNATCH_GRIP_HALF_WIDTH)
        lo, hi = WRIST_DEVIATION_RANGE
        assert lo <= -theta <= hi
        assert feasible < _SNATCH_GRIP_HALF_WIDTH

    def test_clamped_theta_matches_the_wrist_bound(self) -> None:
        spec = BodyModelSpec()
        theta, _ = shoulder_adduct_for_grip(spec, _SNATCH_GRIP_HALF_WIDTH)
        _, wrist_hi = WRIST_DEVIATION_RANGE
        assert theta == pytest.approx(-wrist_hi)

    def test_narrow_grip_is_unaffected(self) -> None:
        """Clean/deadlift/bench's narrower grips need much less abduction
        than either the shoulder or the wrist allows, so they reach their
        full requested width exactly, as before."""
        spec = BodyModelSpec()
        _, feasible = shoulder_adduct_for_grip(spec, _CLEAN_GRIP_HALF_WIDTH)
        assert feasible == pytest.approx(_CLEAN_GRIP_HALF_WIDTH, abs=1e-6)

    def test_rejects_non_finite_grip_offset(self) -> None:
        spec = BodyModelSpec()
        with pytest.raises(ValueError, match="finite"):
            shoulder_adduct_for_grip(spec, float("nan"))
