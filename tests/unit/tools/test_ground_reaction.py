"""Engine-free GRF / CoP math for issue #391 (no OpenSim needed)."""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from opensim_models.tools.ground_reaction import (
    CONTACT_THRESHOLD_N,
    FOOT_SEGMENTS,
    ContactWrench,
    center_of_pressure,
    ground_reaction,
    half_space_wrench,
    inside_polygon,
    support_polygon,
)

AXES = ("X", "Y", "Z")


def _labels(name: str = "force_foot_r_toe") -> list[str]:
    return [
        f"{name}.{side}.{kind}.{axis}"
        for side in ("Sphere", "HalfSpace")
        for kind in ("force", "torque")
        for axis in AXES
    ]


def _cross(p: tuple[float, float, float], f: tuple[float, float, float]):
    return (
        p[1] * f[2] - p[2] * f[1],
        p[2] * f[0] - p[0] * f[2],
        p[0] * f[1] - p[1] * f[0],
    )


def _wrench_at(body: str, point, force) -> ContactWrench:  # type: ignore[no-untyped-def]
    return ContactWrench(body=body, force=force, moment=_cross(point, force))


# --- half_space_wrench --------------------------------------------------------


def test_half_space_wrench_is_the_reaction_on_the_sphere_body() -> None:
    values = [9.0] * 6 + [1.0, -50.0, 2.0, 3.0, 4.0, -5.0]
    force, moment = half_space_wrench(_labels(), values)
    assert force == (-1.0, 50.0, -2.0)
    assert moment == (-3.0, -4.0, 5.0)


def test_half_space_wrench_ignores_label_order() -> None:
    labels = list(reversed(_labels()))
    values = list(reversed([0.0] * 6 + [1.0, -50.0, 2.0, 3.0, 4.0, -5.0]))
    assert half_space_wrench(labels, values)[0] == (-1.0, 50.0, -2.0)


def test_half_space_wrench_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError, match="labels"):
        half_space_wrench(_labels(), [0.0] * 11)


def test_half_space_wrench_rejects_missing_half_space_columns() -> None:
    with pytest.raises(ValueError, match=r"HalfSpace\.torque\.Z"):
        half_space_wrench(_labels()[:-1], [0.0] * 11)


def test_half_space_wrench_rejects_non_finite_values() -> None:
    values = [0.0] * 6 + [math.nan] + [0.0] * 5
    with pytest.raises(ValueError, match="non-finite"):
        half_space_wrench(_labels(), values)


# --- center_of_pressure ---------------------------------------------------------


def test_cop_of_a_point_force_is_its_ground_point() -> None:
    force = (3.0, -2.0, 400.0)
    assert center_of_pressure(force, _cross((0.1, -0.05, 0.0), force)) == (
        pytest.approx((0.1, -0.05, 0.0))
    )


def test_cop_is_none_without_vertical_load() -> None:
    assert center_of_pressure((0.0, 0.0, CONTACT_THRESHOLD_N / 2), (0, 0, 0)) is None
    assert center_of_pressure((0.0, 0.0, -10.0), (0, 0, 0)) is None


@given(
    x=st.floats(-1, 1),
    y=st.floats(-1, 1),
    fx=st.floats(-100, 100),
    fy=st.floats(-100, 100),
    fz=st.floats(1, 2000),
    free=st.floats(-10, 10),
)
def test_cop_recovers_the_application_point_despite_free_moment(
    x: float, y: float, fx: float, fy: float, fz: float, free: float
) -> None:
    mx, my, mz = _cross((x, y, 0.0), (fx, fy, fz))
    cop = center_of_pressure((fx, fy, fz), (mx, my, mz + free))
    assert cop == pytest.approx((x, y, 0.0), abs=1e-9)


# --- ground_reaction ------------------------------------------------------------


def test_ground_reaction_sums_spheres_per_foot_and_in_total() -> None:
    wrenches = [
        _wrench_at("foot_l", (0.1, 0.1, 0.0), (0.0, 0.0, 300.0)),
        _wrench_at("foot_l", (-0.1, 0.1, 0.0), (0.0, 0.0, 100.0)),
        _wrench_at("foot_r", (0.0, -0.1, 0.0), (5.0, 0.0, 400.0)),
    ]
    grf = ground_reaction(wrenches)
    assert grf.feet["foot_l"].force == pytest.approx((0.0, 0.0, 400.0))
    assert grf.feet["foot_l"].cop == pytest.approx((0.05, 0.1, 0.0))
    assert grf.feet["foot_r"].cop == pytest.approx((0.0, -0.1, 0.0))
    assert grf.total.force == pytest.approx((5.0, 0.0, 800.0))
    assert grf.total.cop == pytest.approx((0.025, 0.0, 0.0))
    assert grf.total.in_contact


def test_ground_reaction_without_contact_is_zero_with_no_cop() -> None:
    grf = ground_reaction([_wrench_at("foot_l", (0, 0, 0), (0.0, 0.0, 1e-9))])
    assert set(grf.feet) == set(FOOT_SEGMENTS)
    for reaction in (*grf.feet.values(), grf.total):
        assert reaction.force == (0.0, 0.0, 0.0)
        assert reaction.cop is None
        assert not reaction.in_contact


def test_ground_reaction_on_one_foot_leaves_the_other_out_of_contact() -> None:
    grf = ground_reaction([_wrench_at("foot_r", (0.2, -0.1, 0.0), (0, 0, 700.0))])
    assert grf.feet["foot_l"].cop is None
    assert grf.total.cop == pytest.approx((0.2, -0.1, 0.0))


def test_ground_reaction_ignores_non_foot_contact() -> None:
    grf = ground_reaction([_wrench_at("pelvis", (0, 0, 0.4), (0, 0, 600.0))])
    assert grf.total.cop is None


def test_ground_reaction_rejects_empty_foot_list() -> None:
    with pytest.raises(ValueError, match="feet"):
        ground_reaction([], feet=())


# --- support polygon ------------------------------------------------------------


def test_support_polygon_is_the_counter_clockwise_hull() -> None:
    points = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5), (1, 0)]
    assert support_polygon(points) == [(0, 0), (1, 0), (1, 1), (0, 1)]


def test_support_polygon_needs_three_non_collinear_points() -> None:
    with pytest.raises(ValueError, match="support polygon"):
        support_polygon([(0, 0), (1, 1), (2, 2)])


@pytest.mark.parametrize(
    ("point", "inside"),
    [((0.5, 0.5), True), ((1.0, 0.5), True), ((1.01, 0.5), False), ((-1, -1), False)],
)
def test_inside_polygon(point: tuple[float, float], inside: bool) -> None:
    square = support_polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    assert inside_polygon(point, square) is inside


def test_inside_polygon_rejects_degenerate_polygon() -> None:
    with pytest.raises(ValueError, match="polygon"):
        inside_polygon((0, 0), [(0, 0), (1, 0)])
