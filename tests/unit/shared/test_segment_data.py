"""Tests for shared body segment data helpers.

Guards ``_segment_radius_from_mass`` against non-finite (NaN / +/-inf) and
non-positive mass/length inputs (issue #151).
"""

import math

import pytest

from opensim_models.shared.body._segment_data import _segment_radius_from_mass


class TestSegmentRadiusFromMass:
    def test_accepts_positive_inputs(self) -> None:
        r = _segment_radius_from_mass(mass=5.0, length=0.3)
        assert r > 0.0
        assert math.isfinite(r)

    @pytest.mark.parametrize("length", [0.0, -0.1])
    def test_rejects_nonpositive_length(self, length: float) -> None:
        with pytest.raises(ValueError, match="Segment length"):
            _segment_radius_from_mass(mass=1.0, length=length)

    @pytest.mark.parametrize("mass", [0.0, -2.0])
    def test_rejects_nonpositive_mass(self, mass: float) -> None:
        with pytest.raises(ValueError, match="Segment mass"):
            _segment_radius_from_mass(mass=mass, length=0.3)

    @pytest.mark.parametrize("length", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_length(self, length: float) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            _segment_radius_from_mass(mass=1.0, length=length)

    @pytest.mark.parametrize("mass", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_mass(self, mass: float) -> None:
        with pytest.raises(ValueError, match="non-finite"):
            _segment_radius_from_mass(mass=mass, length=0.3)
