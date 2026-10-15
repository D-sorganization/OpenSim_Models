"""Tests for the opt-in segmental lumbar chain (issue #464).

The coupling ratios used here are synthetic test fixtures chosen only to
exercise the builder. They are NOT published values.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from opensim_models.exercises.base import ExerciseConfig
from opensim_models.exercises.deadlift.deadlift_model import DeadliftModelBuilder
from opensim_models.shared.body import BodyModelSpec, create_full_body
from opensim_models.shared.body.lumbar_chain import (
    LUMBAR_LEVELS,
    LumbarCouplingLaw,
    uniform_lumbar_law,
)
from opensim_models.shared.parity.standard import JOINT_LIMITS

MOTIONS = ("flex", "lateral", "rotate")
AXES = {"flex": (0, 0, -1), "lateral": (-1, 0, 0), "rotate": (0, 1, 0)}
TOL = 1e-9
BODY_CHAIN = ["pelvis", "lumbar_L5", "lumbar_L4", "lumbar_L3", "lumbar_L2", "torso"]

# Synthetic, unequal, caudal-first shares (each sums to exactly 1).
FIXTURE_RATIOS = {
    "flex": (0.30, 0.25, 0.20, 0.15, 0.10),
    "lateral": (0.10, 0.15, 0.20, 0.25, 0.30),
    "rotate": (0.40, 0.30, 0.15, 0.10, 0.05),
}


def _law() -> LumbarCouplingLaw:
    return LumbarCouplingLaw(
        law_id="synthetic_test_fixture",
        version="0",
        source="synthetic test fixture, not a published law",
        ratios=FIXTURE_RATIOS,
    )


def _build(law: LumbarCouplingLaw | None):
    bodyset, jointset = ET.Element("BodySet"), ET.Element("JointSet")
    kwargs = {}
    constraintset = None
    if law is not None:
        constraintset = ET.Element("ConstraintSet")
        kwargs = {"lumbar_chain": law, "constraintset": constraintset}
    bodies = create_full_body(bodyset, jointset, BodyModelSpec(), **kwargs)
    return bodyset, jointset, constraintset, bodies


def _joint(jointset: ET.Element, name: str) -> ET.Element:
    found = [j for j in jointset.findall("CustomJoint") if j.get("name") == name]
    assert len(found) == 1, name
    return found[0]


def _rot(axis: np.ndarray, angle: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    k = np.array(
        [[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]]
    )
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def _slope(function_owner: ET.Element) -> float:
    return float(function_owner.find(".//LinearFunction/coefficients").text.split()[0])


def _joint_rotation(joint: ET.Element, q: dict[str, float]) -> np.ndarray:
    """Parent-to-child rotation of a CustomJoint from its parsed XML."""
    result = np.eye(3)
    axes = {
        t.get("name"): t
        for t in joint.find("SpatialTransform").findall("TransformAxis")
    }
    for i in (1, 2, 3):
        ta = axes[f"rotation{i}"]
        coord = ta.findtext("coordinates")
        if coord is None:
            continue
        axis = np.array([float(v) for v in ta.findtext("axis").split()])
        result = result @ _rot(axis, _slope(ta) * q.get(coord, 0.0))
    return result


def _joint_translation(joint: ET.Element) -> np.ndarray:
    total = np.zeros(3)
    for frame in joint.findall("PhysicalOffsetFrame"):
        sign = 1.0 if frame.get("name").endswith("_parent") else -1.0
        vec = [float(v) for v in frame.findtext("translation").split()]
        total += sign * np.array(vec)
    return total


def _constraints(constraintset: ET.Element) -> dict[str, ET.Element]:
    return {
        c.findtext("dependent_coordinate_name"): c
        for c in constraintset.findall("CoordinateCouplerConstraint")
    }


def _level_joint_names() -> list[str]:
    return [f"lumbar_{lvl}" for lvl in LUMBAR_LEVELS]


def _coordinate_values(
    constraintset: ET.Element, drivers: dict[str, float]
) -> dict[str, float]:
    values = dict(drivers)
    for dep, c in _constraints(constraintset).items():
        driver = c.findtext("independent_coordinate_names")
        values[dep] = _slope(c) * drivers.get(driver, 0.0)
    return values


def _composed(jointset: ET.Element, values: dict[str, float]) -> np.ndarray:
    composed = np.eye(3)
    for name in _level_joint_names():
        composed = composed @ _joint_rotation(_joint(jointset, name), values)
    return composed


class TestLaw:
    def test_levels_are_caudal_first(self):
        assert LUMBAR_LEVELS == ("L5_S1", "L4_L5", "L3_L4", "L2_L3", "L1_L2")

    def test_valid_law_exposes_provenance(self):
        law = _law()
        assert "synthetic_test_fixture" in law.provenance
        assert "not a published law" in law.provenance

    @pytest.mark.parametrize("motion", MOTIONS)
    def test_ratios_must_sum_to_one(self, motion):
        bad = {**FIXTURE_RATIOS, motion: (0.3, 0.25, 0.2, 0.15, 0.2)}
        with pytest.raises(ValueError, match="sum to 1"):
            LumbarCouplingLaw("x", "0", "src", bad)

    def test_ratios_need_five_levels(self):
        bad = {**FIXTURE_RATIOS, "flex": (0.5, 0.5)}
        with pytest.raises(ValueError, match="5 levels"):
            LumbarCouplingLaw("x", "0", "src", bad)

    def test_ratios_need_all_motions(self):
        bad = {k: v for k, v in FIXTURE_RATIOS.items() if k != "rotate"}
        with pytest.raises(ValueError, match="rotate"):
            LumbarCouplingLaw("x", "0", "src", bad)

    @pytest.mark.parametrize("value", [0.0, -0.1, float("nan")])
    def test_ratios_must_be_positive_finite(self, value):
        bad = {**FIXTURE_RATIOS, "flex": (value, 0.4, 0.3, 0.2, 0.1)}
        with pytest.raises(ValueError):
            LumbarCouplingLaw("x", "0", "src", bad)

    @pytest.mark.parametrize("field", ["law_id", "version", "source"])
    def test_provenance_fields_must_not_be_blank(self, field):
        args = {"law_id": "x", "version": "0", "source": "src"}
        args[field] = "  "
        with pytest.raises(ValueError, match=field):
            LumbarCouplingLaw(ratios=FIXTURE_RATIOS, **args)

    def test_uniform_law_is_labelled_unpublished(self):
        law = uniform_lumbar_law()
        for motion in MOTIONS:
            assert law.ratios[motion] == (0.2,) * 5
        assert "not a published" in law.provenance


class TestDefaultUnchanged:
    def test_default_has_single_lumbar_joint(self):
        _, jointset, _, bodies = _build(None)
        assert _joint(jointset, "lumbar") is not None
        assert not any(n.startswith("lumbar_L") for n in bodies)
        assert not any((j.get("name") or "").startswith("lumbar_L") for j in jointset)

    def test_default_builder_output_has_no_chain_artifacts(self):
        xml = DeadliftModelBuilder().build()
        assert "CoordinateCouplerConstraint" not in xml
        assert "publications" not in xml
        assert "lumbar_L" not in xml


class TestChain:
    def test_five_level_joints_replace_the_single_joint(self):
        _, jointset, _, _ = _build(_law())
        names = [j.get("name") for j in jointset.findall("CustomJoint")]
        assert "lumbar" not in names
        for name in _level_joint_names():
            assert name in names

    def test_joints_chain_pelvis_to_torso(self):
        _, jointset, _, bodies = _build(_law())
        for upper, lower, name in zip(
            BODY_CHAIN[:-1], BODY_CHAIN[1:], _level_joint_names(), strict=True
        ):
            frames = {
                f.get("name"): f.findtext("socket_parent")
                for f in _joint(jointset, name).findall("PhysicalOffsetFrame")
            }
            assert frames[f"{name}_parent"] == f"/bodyset/{upper}"
            assert frames[f"{name}_child"] == f"/bodyset/{lower}"
        for body in BODY_CHAIN:
            assert body in bodies

    def test_intermediate_bodies_have_positive_mass(self):
        bodyset, _, _, _ = _build(_law())
        for name in BODY_CHAIN[1:-1]:
            body = next(b for b in bodyset if b.get("name") == name)
            assert float(body.findtext("mass")) > 0.0

    def test_neutral_torso_placement_matches_default(self):
        _, default_joints, _, _ = _build(None)
        _, joints, _, _ = _build(_law())
        default = _joint_translation(_joint(default_joints, "lumbar"))
        chain = sum(_joint_translation(_joint(joints, n)) for n in _level_joint_names())
        assert np.allclose(chain, default, atol=TOL)

    def test_only_driver_coordinates_are_free(self):
        _, jointset, constraintset, _ = _build(_law())
        coords = [
            c.get("name")
            for n in _level_joint_names()
            for c in _joint(jointset, n).find("coordinates")
        ]
        assert len(coords) == 15
        dependents = set(_constraints(constraintset))
        assert len(dependents) == 12
        assert set(coords) - dependents == {
            "lumbar_flex",
            "lumbar_lateral",
            "lumbar_rotate",
        }

    @pytest.mark.parametrize("motion", MOTIONS)
    def test_coupler_ratios_match_the_law_and_sum_to_one(self, motion):
        _, jointset, constraintset, _ = _build(_law())
        constraints = _constraints(constraintset)
        driver = f"lumbar_{motion}"
        slopes = []
        for level, ratio in zip(LUMBAR_LEVELS, FIXTURE_RATIOS[motion], strict=True):
            if level == LUMBAR_LEVELS[0]:
                # The first level is driven directly with the law's ratio.
                ta = next(
                    t
                    for t in _joint(jointset, f"lumbar_{level}").iter("TransformAxis")
                    if t.findtext("coordinates") == driver
                )
                slopes.append(_slope(ta))
            else:
                c = constraints[f"{driver}_{level}"]
                assert c.findtext("independent_coordinate_names") == driver
                coeffs = c.find(".//LinearFunction/coefficients").text.split()
                assert float(coeffs[1]) == 0.0
                slopes.append(float(coeffs[0]))
            assert abs(slopes[-1] - ratio) < TOL
        assert abs(sum(slopes) - 1.0) < TOL

    @pytest.mark.parametrize("motion", MOTIONS)
    def test_total_rom_is_preserved(self, motion):
        _, jointset, _, _ = _build(_law())
        lo, hi = JOINT_LIMITS[f"lumbar_{motion}"]
        driver = f"lumbar_{motion}"
        total_min = total_max = 0.0
        for level, ratio in zip(LUMBAR_LEVELS, FIXTURE_RATIOS[motion], strict=True):
            name = driver if level == LUMBAR_LEVELS[0] else f"{driver}_{level}"
            coords = _joint(jointset, f"lumbar_{level}").find("coordinates")
            coord = next(c for c in coords if c.get("name") == name)
            cmin, cmax = (float(v) for v in coord.findtext("range").split())
            if level == LUMBAR_LEVELS[0]:
                # The driver carries the total range; its level angle is ratio * q.
                assert abs(cmin - lo) < TOL and abs(cmax - hi) < TOL
                cmin, cmax = ratio * cmin, ratio * cmax
            assert abs(cmin - ratio * lo) < TOL and abs(cmax - ratio * hi) < TOL
            total_min += cmin
            total_max += cmax
        assert abs(total_min - lo) < TOL and abs(total_max - hi) < TOL

    @pytest.mark.parametrize("motion", MOTIONS)
    def test_composition_equals_single_axis_rotation_by_total(self, motion):
        """Collinear level axes compose to one rotation by the driver angle."""
        _, jointset, constraintset, _ = _build(_law())
        q = 0.3
        values = _coordinate_values(constraintset, {f"lumbar_{motion}": q})
        composed = _composed(jointset, values)
        assert np.allclose(composed, _rot(np.array(AXES[motion], float), q), atol=TOL)

    def test_composition_equals_product_of_level_transforms(self):
        """Mixed motions: composed rotation equals the caudal-first product."""
        _, jointset, constraintset, _ = _build(_law())
        drivers = {"lumbar_flex": 0.4, "lumbar_lateral": -0.25, "lumbar_rotate": 0.3}
        composed = _composed(jointset, _coordinate_values(constraintset, drivers))
        expected = np.eye(3)
        for i in range(5):
            level = np.eye(3)
            for motion in MOTIONS:
                angle = FIXTURE_RATIOS[motion][i] * drivers[f"lumbar_{motion}"]
                level = level @ _rot(np.array(AXES[motion], float), angle)
            expected = expected @ level
        assert np.allclose(composed, expected, atol=TOL)

    def test_requires_constraintset(self):
        with pytest.raises(ValueError, match="constraintset"):
            create_full_body(
                ET.Element("BodySet"),
                ET.Element("JointSet"),
                BodyModelSpec(),
                lumbar_chain=_law(),
            )


class TestExerciseIntegration:
    def test_flag_off_matches_explicit_none(self):
        assert (
            DeadliftModelBuilder().build()
            == DeadliftModelBuilder(ExerciseConfig(lumbar_chain=None)).build()
        )

    def test_flag_on_builds_a_valid_model_that_records_the_law(self):
        xml = DeadliftModelBuilder(ExerciseConfig(lumbar_chain=_law())).build()
        root = ET.fromstring(xml)
        assert len(root.findall(".//CoordinateCouplerConstraint")) == 12
        publications = root.findtext(".//publications")
        assert publications is not None
        assert "synthetic_test_fixture" in publications
        assert "not a published law" in publications

    def test_flag_on_keeps_pose_coordinates_valid(self):
        """lumbar_flex et al. remain the driver coordinates for via-poses."""
        xml = DeadliftModelBuilder(ExerciseConfig(lumbar_chain=_law())).build()
        root = ET.fromstring(xml)
        names = {c.get("name") for c in root.iter("Coordinate")}
        assert {"lumbar_flex", "lumbar_lateral", "lumbar_rotate"} <= names
