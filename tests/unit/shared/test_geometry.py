"""Tests for geometry and inertia utilities."""

import math

import numpy as np
import pytest

from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    hollow_cylinder_inertia,
    parallel_axis_shift,
    rectangular_prism_inertia,
    rotation_matrix_x,
    rotation_matrix_y,
    rotation_matrix_z,
    sphere_inertia,
)


class TestCylinderInertia:
    def test_known_values(self):
        """1 kg cylinder, r=0.1 m, L=1.0 m."""
        ixx, iyy, izz = cylinder_inertia(1.0, 0.1, 1.0)
        assert iyy == pytest.approx(0.5 * 1.0 * 0.1**2)
        assert ixx == pytest.approx((1.0 / 12.0) * (3 * 0.01 + 1.0))
        assert izz == pytest.approx(ixx)

    def test_rejects_zero_mass(self):
        with pytest.raises(ValueError, match="must be positive"):
            cylinder_inertia(0, 0.1, 1.0)

    def test_rejects_negative_radius(self):
        with pytest.raises(ValueError, match="must be positive"):
            cylinder_inertia(1.0, -0.1, 1.0)

    def test_symmetry(self):
        """Ixx should equal Izz for a cylinder aligned along Y."""
        ixx, _, izz = cylinder_inertia(5.0, 0.05, 2.0)
        assert ixx == pytest.approx(izz)


class TestHollowCylinderInertia:
    def test_known_values(self):
        """Olympic barbell sleeve: 1 kg, inner=0.025 m, outer=0.029 m, L=0.445 m."""
        ixx, iyy, izz = hollow_cylinder_inertia(1.0, 0.025, 0.029, 0.445)
        r_sq_sum = 0.025**2 + 0.029**2
        assert iyy == pytest.approx(0.5 * 1.0 * r_sq_sum)
        assert ixx == pytest.approx((1.0 / 12.0) * (3.0 * r_sq_sum + 0.445**2))
        assert izz == pytest.approx(ixx)

    def test_symmetry_ixx_equals_izz(self):
        ixx, _, izz = hollow_cylinder_inertia(2.0, 0.01, 0.05, 0.30)
        assert ixx == pytest.approx(izz)

    def test_greater_than_solid_cylinder_axial(self):
        """Hollow cylinder has higher axial inertia than solid of same mass and outer radius."""
        ixx_h, iyy_h, _ = hollow_cylinder_inertia(1.0, 0.01, 0.05, 0.30)
        ixx_s, iyy_s, _ = cylinder_inertia(1.0, 0.05, 0.30)
        assert iyy_h > iyy_s

    def test_rejects_zero_mass(self):
        with pytest.raises(ValueError, match="must be positive"):
            hollow_cylinder_inertia(0.0, 0.025, 0.029, 0.445)

    def test_rejects_inner_greater_than_outer(self):
        with pytest.raises(ValueError, match="inner_radius"):
            hollow_cylinder_inertia(1.0, 0.05, 0.03, 0.445)

    def test_rejects_inner_equal_outer(self):
        with pytest.raises(ValueError, match="inner_radius"):
            hollow_cylinder_inertia(1.0, 0.025, 0.025, 0.445)

    def test_rejects_negative_length(self):
        with pytest.raises(ValueError, match="must be positive"):
            hollow_cylinder_inertia(1.0, 0.025, 0.029, -0.1)


class TestRectangularPrismInertia:
    def test_cube(self):
        """A cube should have equal inertias on all axes."""
        ixx, iyy, izz = rectangular_prism_inertia(1.0, 1.0, 1.0, 1.0)
        assert ixx == pytest.approx(iyy)
        assert iyy == pytest.approx(izz)

    def test_known_values(self):
        """2 kg box: 0.5 x 0.3 x 0.2 m."""
        ixx, iyy, izz = rectangular_prism_inertia(2.0, 0.5, 0.3, 0.2)
        assert ixx == pytest.approx((2.0 / 12.0) * (0.09 + 0.04))
        assert iyy == pytest.approx((2.0 / 12.0) * (0.25 + 0.04))
        assert izz == pytest.approx((2.0 / 12.0) * (0.25 + 0.09))


class TestSphereInertia:
    def test_uniform(self):
        """Sphere has equal inertia on all axes."""
        ixx, iyy, izz = sphere_inertia(10.0, 0.5)
        expected = (2.0 / 5.0) * 10.0 * 0.25
        assert ixx == pytest.approx(expected)
        assert iyy == pytest.approx(expected)
        assert izz == pytest.approx(expected)


class TestParallelAxisShift:
    def test_zero_displacement(self):
        """No shift should return original inertia."""
        result = parallel_axis_shift(1.0, (1.0, 1.0, 1.0), np.zeros(3))
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(1.0)
        assert result[2] == pytest.approx(1.0)

    def test_increases_inertia(self):
        """Shifting away from CoM always increases inertia."""
        original = (0.1, 0.1, 0.1)
        shifted = parallel_axis_shift(5.0, original, np.array([0.5, 0, 0]))
        assert shifted[0] == pytest.approx(0.1)  # X displacement doesn't affect Ixx
        assert shifted[1] > original[1]
        assert shifted[2] > original[2]


class TestRotationMatrices:
    def test_identity_at_zero(self):
        for fn in [rotation_matrix_x, rotation_matrix_y, rotation_matrix_z]:
            mat = fn(0.0)
            np.testing.assert_allclose(mat, np.eye(3), atol=1e-15)

    def test_orthogonality(self):
        for fn in [rotation_matrix_x, rotation_matrix_y, rotation_matrix_z]:
            mat = fn(0.7854)
            product = mat @ mat.T
            np.testing.assert_allclose(product, np.eye(3), atol=1e-12)

    def test_determinant_is_one(self):
        for fn in [rotation_matrix_x, rotation_matrix_y, rotation_matrix_z]:
            mat = fn(1.2345)
            assert np.linalg.det(mat) == pytest.approx(1.0)

    def test_90_degree_rotation_z(self):
        mat = rotation_matrix_z(math.pi / 2)
        vec = mat @ np.array([1, 0, 0])
        np.testing.assert_allclose(vec, [0, 1, 0], atol=1e-12)
