"""Hypothesis property-based tests for geometry and model invariants."""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from opensim_models.shared.barbell.barbell_model import BarbellSpec
from opensim_models.shared.body.body_model import BodyModelSpec
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    parallel_axis_shift,
    rectangular_prism_inertia,
    sphere_inertia,
)

# --- Strategies ---

positive_float = st.floats(min_value=0.01, max_value=1e4, allow_nan=False)
small_positive = st.floats(min_value=0.01, max_value=100.0, allow_nan=False)


class TestCylinderInertiaProperties:
    """Property-based tests for cylinder inertia computation."""

    @given(mass=positive_float, radius=positive_float, length=positive_float)
    @settings(max_examples=50)
    def test_all_components_positive(self, mass, radius, length):
        ixx, iyy, izz = cylinder_inertia(mass, radius, length)
        assert ixx > 0
        assert iyy > 0
        assert izz > 0

    @given(mass=positive_float, radius=positive_float, length=positive_float)
    @settings(max_examples=50)
    def test_triangle_inequality(self, mass, radius, length):
        ixx, iyy, izz = cylinder_inertia(mass, radius, length)
        assert ixx + iyy >= izz
        assert ixx + izz >= iyy
        assert iyy + izz >= ixx

    @given(mass=positive_float, radius=positive_float, length=positive_float)
    @settings(max_examples=50)
    def test_transverse_symmetry(self, mass, radius, length):
        ixx, _, izz = cylinder_inertia(mass, radius, length)
        assert math.isclose(ixx, izz, rel_tol=1e-12)

    @given(mass=positive_float, radius=positive_float, length=positive_float)
    @settings(max_examples=50)
    def test_scales_linearly_with_mass(self, mass, radius, length):
        i1 = cylinder_inertia(mass, radius, length)
        i2 = cylinder_inertia(2 * mass, radius, length)
        for a, b in zip(i1, i2, strict=True):
            assert math.isclose(2 * a, b, rel_tol=1e-10)


class TestRectangularPrismInertiaProperties:
    @given(
        mass=positive_float,
        w=positive_float,
        h=positive_float,
        d=positive_float,
    )
    @settings(max_examples=50)
    def test_all_positive(self, mass, w, h, d):
        ixx, iyy, izz = rectangular_prism_inertia(mass, w, h, d)
        assert ixx > 0
        assert iyy > 0
        assert izz > 0

    @given(mass=positive_float, side=positive_float)
    @settings(max_examples=50)
    def test_cube_symmetry(self, mass, side):
        ixx, iyy, izz = rectangular_prism_inertia(mass, side, side, side)
        assert math.isclose(ixx, iyy, rel_tol=1e-12)
        assert math.isclose(iyy, izz, rel_tol=1e-12)


class TestSphereInertiaProperties:
    @given(mass=positive_float, radius=positive_float)
    @settings(max_examples=50)
    def test_isotropic(self, mass, radius):
        ixx, iyy, izz = sphere_inertia(mass, radius)
        assert math.isclose(ixx, iyy, rel_tol=1e-12)
        assert math.isclose(iyy, izz, rel_tol=1e-12)

    @given(mass=positive_float, radius=positive_float)
    @settings(max_examples=50)
    def test_exact_formula(self, mass, radius):
        ixx, _, _ = sphere_inertia(mass, radius)
        expected = 0.4 * mass * radius**2
        assert math.isclose(ixx, expected, rel_tol=1e-12)


class TestParallelAxisProperties:
    @given(mass=positive_float, radius=positive_float)
    @settings(max_examples=50)
    def test_zero_displacement_identity(self, mass, radius):
        import numpy as np

        inertia = sphere_inertia(mass, radius)
        shifted = parallel_axis_shift(mass, inertia, np.zeros(3))
        for a, b in zip(inertia, shifted, strict=True):
            assert math.isclose(a, b, rel_tol=1e-12)

    @given(
        mass=positive_float,
        radius=positive_float,
        dx=st.floats(min_value=-10, max_value=10, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_shift_increases_inertia(self, mass, radius, dx):
        import numpy as np

        if abs(dx) < 1e-10:
            return
        inertia = sphere_inertia(mass, radius)
        shifted = parallel_axis_shift(mass, inertia, np.array([dx, 0, 0]))
        # Iyy and Izz should increase; Ixx stays the same (shift along x)
        assert shifted[1] >= inertia[1] - 1e-10
        assert shifted[2] >= inertia[2] - 1e-10


class TestBodyModelSpecProperties:
    @given(
        mass=st.floats(min_value=1.0, max_value=500.0, allow_nan=False),
        height=st.floats(min_value=0.5, max_value=3.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_valid_specs_accepted(self, mass, height):
        spec = BodyModelSpec(total_mass=mass, height=height)
        assert spec.total_mass == mass
        assert spec.height == height


class TestBarbellSpecProperties:
    @given(plate_mass=st.floats(min_value=0, max_value=200, allow_nan=False))
    @settings(max_examples=30)
    def test_total_mass_consistent(self, plate_mass):
        spec = BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass)
        expected = 20.0 + 2 * plate_mass
        assert math.isclose(spec.total_mass, expected, rel_tol=1e-12)

    @given(plate_mass=st.floats(min_value=0, max_value=200, allow_nan=False))
    @settings(max_examples=30)
    def test_sleeve_length_positive(self, plate_mass):
        spec = BarbellSpec.mens_olympic(plate_mass_per_side=plate_mass)
        assert spec.sleeve_length > 0

    def test_negative_plate_mass_rejected(self):
        with pytest.raises(ValueError):
            BarbellSpec.mens_olympic(plate_mass_per_side=-10)
