"""Edge-case and boundary condition tests."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import numpy as np
import pytest

from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.bench_press.bench_press_model import (
    BenchPressModelBuilder,
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import build_deadlift_model
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model
from opensim_models.shared.barbell.barbell_model import BarbellSpec
from opensim_models.shared.body.body_model import BodyModelSpec
from opensim_models.shared.contracts.postconditions import (
    ensure_positive_definite_inertia,
    ensure_positive_mass,
    ensure_valid_xml,
)
from opensim_models.shared.contracts.preconditions import (
    require_finite,
    require_in_range,
    require_non_negative,
    require_positive,
    require_shape,
    require_unit_vector,
)
from opensim_models.shared.utils.geometry import (
    cylinder_inertia,
    rectangular_prism_inertia,
    sphere_inertia,
)


class TestPreconditionEdgeCases:
    """Edge cases for precondition checks."""

    def test_require_positive_zero(self):
        with pytest.raises(ValueError, match="must be positive"):
            require_positive(0.0, "val")

    def test_require_positive_negative(self):
        with pytest.raises(ValueError, match="must be positive"):
            require_positive(-1e-10, "val")

    def test_require_non_negative_negative(self):
        with pytest.raises(ValueError, match="must be non-negative"):
            require_non_negative(-0.001, "val")

    def test_require_non_negative_zero_ok(self):
        require_non_negative(0.0, "val")  # should not raise

    def test_require_unit_vector_wrong_shape(self):
        with pytest.raises(ValueError, match="3-vector"):
            require_unit_vector([1.0, 0.0], "vec")

    def test_require_unit_vector_not_unit(self):
        with pytest.raises(ValueError, match="unit-length"):
            require_unit_vector([1.0, 1.0, 0.0], "vec")

    def test_require_unit_vector_valid(self):
        require_unit_vector([0.0, 0.0, 1.0], "vec")

    def test_require_finite_with_nan(self):
        with pytest.raises(ValueError, match="non-finite"):
            require_finite([1.0, float("nan"), 3.0], "arr")

    def test_require_finite_with_inf(self):
        with pytest.raises(ValueError, match="non-finite"):
            require_finite([float("inf")], "arr")

    def test_require_in_range_below(self):
        with pytest.raises(ValueError):
            require_in_range(-1.0, 0.0, 10.0, "val")

    def test_require_in_range_above(self):
        with pytest.raises(ValueError):
            require_in_range(11.0, 0.0, 10.0, "val")

    def test_require_in_range_boundary(self):
        require_in_range(0.0, 0.0, 10.0, "val")  # boundary should be ok
        require_in_range(10.0, 0.0, 10.0, "val")

    def test_require_shape_mismatch(self):
        with pytest.raises(ValueError, match="shape"):
            require_shape(np.array([1, 2, 3]), (2,), "arr")


class TestPostconditionEdgeCases:
    def test_ensure_valid_xml_empty_string(self):
        with pytest.raises(ValueError):
            ensure_valid_xml("")

    def test_ensure_positive_mass_negative(self):
        with pytest.raises(ValueError, match="not positive"):
            ensure_positive_mass(-1.0, "test_body")

    def test_ensure_inertia_single_zero(self):
        with pytest.raises(ValueError):
            ensure_positive_definite_inertia(0.0, 1.0, 1.0, "body")

    def test_ensure_inertia_triangle_violation(self):
        with pytest.raises(ValueError, match="triangle"):
            ensure_positive_definite_inertia(0.01, 0.01, 100.0, "body")


class TestGeometryEdgeCases:
    def test_cylinder_zero_mass_rejected(self):
        with pytest.raises(ValueError):
            cylinder_inertia(0.0, 0.1, 0.5)

    def test_cylinder_zero_radius_rejected(self):
        with pytest.raises(ValueError):
            cylinder_inertia(1.0, 0.0, 0.5)

    def test_rectangular_prism_zero_dimension_rejected(self):
        with pytest.raises(ValueError):
            rectangular_prism_inertia(1.0, 0.0, 1.0, 1.0)

    def test_sphere_zero_mass_rejected(self):
        with pytest.raises(ValueError):
            sphere_inertia(0.0, 0.1)

    def test_very_small_cylinder(self):
        """Very small but valid dimensions should produce valid inertias."""
        ixx, iyy, izz = cylinder_inertia(0.001, 0.001, 0.001)
        assert ixx > 0
        assert iyy > 0
        assert izz > 0

    def test_very_large_cylinder(self):
        """Very large dimensions should still produce valid inertias."""
        ixx, iyy, izz = cylinder_inertia(1e4, 10.0, 100.0)
        assert ixx > 0
        assert iyy > 0
        assert izz > 0


class TestBarbellSpecEdgeCases:
    def test_shaft_longer_than_total_rejected(self):
        with pytest.raises(ValueError, match="shaft_length"):
            BarbellSpec(total_length=2.0, shaft_length=2.5)

    def test_shaft_equal_to_total_rejected(self):
        with pytest.raises(ValueError, match="shaft_length"):
            BarbellSpec(total_length=2.0, shaft_length=2.0)

    def test_zero_bar_mass_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            BarbellSpec(bar_mass=0.0)

    def test_negative_plate_mass_rejected(self):
        with pytest.raises(ValueError, match="must be non-negative"):
            BarbellSpec(plate_mass_per_side=-5.0)

    def test_zero_plate_mass_ok(self):
        spec = BarbellSpec(plate_mass_per_side=0.0)
        assert spec.total_mass == spec.bar_mass  # type: ignore

    def test_womens_bar_dimensions(self):
        spec = BarbellSpec.womens_olympic()
        assert spec.bar_mass == 15.0  # type: ignore
        assert spec.total_length == 2.01


class TestBodyModelSpecEdgeCases:
    def test_zero_mass_rejected(self):
        with pytest.raises(ValueError):
            BodyModelSpec(total_mass=0.0)

    def test_negative_height_rejected(self):
        with pytest.raises(ValueError):
            BodyModelSpec(height=-1.0)

    def test_extreme_anthropometrics(self):
        """Very tall/heavy person should still produce valid model."""
        spec = BodyModelSpec(total_mass=200.0, height=2.20)
        assert spec.total_mass == 200.0  # type: ignore

    def test_small_person(self):
        """Small person (child) should still produce valid model."""
        spec = BodyModelSpec(total_mass=30.0, height=1.20)
        assert spec.height == 1.20


class TestModelBuildEdgeCases:
    def test_zero_plate_mass_produces_valid_xml(self):
        xml_str = build_squat_model(plate_mass_per_side=0.0)
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_all_exercises_produce_valid_xml(self):
        """All five exercises should produce well-formed XML."""
        builders = [
            build_squat_model,
            build_bench_press_model,
            build_deadlift_model,
            build_snatch_model,
            build_clean_and_jerk_model,
        ]
        for builder in builders:
            xml_str = builder()
            root = ET.fromstring(xml_str)
            assert root.tag == "OpenSimDocument"

    def test_bench_press_bilateral_attachment(self):
        """Bench press should attach barbell to both hands."""
        xml_str = build_bench_press_model()
        root = ET.fromstring(xml_str)
        jointset = root.find(".//JointSet")
        joint_names = [j.get("name", "") for j in jointset]  # type: ignore
        assert "barbell_to_left_hand" in joint_names
        assert "barbell_to_right_hand" in joint_names

    def test_extreme_plate_mass(self):
        """Very heavy plates should still build a valid model."""
        xml_str = build_deadlift_model(plate_mass_per_side=200.0)
        root = ET.fromstring(xml_str)
        assert root.tag == "OpenSimDocument"

    def test_custom_config_accepted(self):
        """Custom ExerciseConfig should be accepted by builders."""
        config = ExerciseConfig(
            body_spec=BodyModelSpec(total_mass=100.0, height=1.90),
            barbell_spec=BarbellSpec.womens_olympic(plate_mass_per_side=30.0),
        )
        builder = BenchPressModelBuilder(config)
        xml_str = builder.build()
        root = ET.fromstring(xml_str)
        assert root.find(".//Model").get("name") == "bench_press"  # type: ignore
