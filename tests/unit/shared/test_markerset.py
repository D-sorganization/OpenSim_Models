# SPDX-License-Identifier: MIT
"""Unit tests for OpenSim MarkerSet generation (#387)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises
from opensim_models.shared.body import BodyModelSpec
from opensim_models.shared.body._segment_data import _seg

pytestmark = [pytest.mark.unit]

EXERCISES = list_exercises()
BARBELL_EXERCISES = ("squat", "deadlift", "bench_press", "snatch", "clean_and_jerk")
BODYWEIGHT_EXERCISES = ("gait", "sit_to_stand")

STANDARD_HUMAN_MARKERS: tuple[str, ...] = (
    "pelvis",
    "torso",
    "head",
    "upper_arm_l",
    "upper_arm_r",
    "forearm_l",
    "forearm_r",
    "hand_l",
    "hand_r",
    "thigh_l",
    "thigh_r",
    "shank_l",
    "shank_r",
    "foot_l",
    "foot_r",
)


def _get_markerset(xml_str: str) -> ET.Element:
    root = ET.fromstring(xml_str)
    model = root.find("Model") if root.tag != "Model" else root
    assert model is not None, "Model element missing in XML"
    ms = model.find("MarkerSet")
    assert ms is not None, "MarkerSet element missing in Model"
    return ms


def _get_marker_dict(xml_str: str) -> dict[str, tuple[str, tuple[float, float, float]]]:
    """Return mapping: marker_name -> (parent_frame, (x, y, z))."""
    ms = _get_markerset(xml_str)
    markers = ms.findall(".//Marker")
    out: dict[str, tuple[str, tuple[float, float, float]]] = {}
    for m in markers:
        name = m.get("name")
        assert name, "Marker missing name attribute"
        socket = m.find("socket_parent_frame")
        assert socket is not None and socket.text, (
            f"Marker {name} missing socket_parent_frame"
        )
        loc_el = m.find("location")
        assert loc_el is not None and loc_el.text, f"Marker {name} missing location"
        coords = tuple(float(v) for v in loc_el.text.strip().split())
        assert len(coords) == 3, f"Marker {name} location must have 3 coordinates"
        out[name] = (socket.text.strip(), coords)
    return out


@pytest.mark.parametrize("exercise", EXERCISES)
def test_all_models_have_markerset_with_human_markers(exercise: str) -> None:
    """Every generated model includes a MarkerSet with all canonical human markers."""
    xml_str = EXERCISE_BUILDERS[exercise]()
    markers = _get_marker_dict(xml_str)

    for m_name in STANDARD_HUMAN_MARKERS:
        assert m_name in markers, f"{exercise} missing standard marker {m_name!r}"
        parent_frame, _ = markers[m_name]
        assert parent_frame == f"/bodyset/{m_name}", (
            f"{exercise} marker {m_name} has unexpected parent frame {parent_frame!r}"
        )


@pytest.mark.parametrize("exercise", BARBELL_EXERCISES)
def test_barbell_exercises_have_bar_marker(exercise: str) -> None:
    """Barbell exercises include bar marker on barbell_shaft."""
    xml_str = EXERCISE_BUILDERS[exercise]()
    markers = _get_marker_dict(xml_str)
    assert "bar" in markers or "barbell_shaft" in markers, (
        f"{exercise} missing bar marker in MarkerSet"
    )
    bar_name = "bar" if "bar" in markers else "barbell_shaft"
    parent_frame, pos = markers[bar_name]
    assert parent_frame == "/bodyset/barbell_shaft"
    assert pos == (0.0, 0.0, 0.0)


@pytest.mark.parametrize("exercise", BODYWEIGHT_EXERCISES)
def test_bodyweight_exercises_do_not_have_bar_marker(exercise: str) -> None:
    """Bodyweight exercises do not include bar marker."""
    xml_str = EXERCISE_BUILDERS[exercise]()
    markers = _get_marker_dict(xml_str)
    assert "bar" not in markers
    assert "barbell_shaft" not in markers


def test_marker_locations_match_segment_geometry() -> None:
    """Marker locations match segment geometry defined in BodyModelSpec."""
    spec = BodyModelSpec()
    xml_str = EXERCISE_BUILDERS["gait"]()
    markers = _get_marker_dict(xml_str)

    # Pelvis marker is at origin
    assert markers["pelvis"][1] == (0.0, 0.0, 0.0)

    # Torso and head markers are displaced along +Y by segment length
    _, torso_len, _ = _seg(spec, "torso")
    assert markers["torso"][1][1] == pytest.approx(torso_len, abs=1e-4)

    _, head_len, _ = _seg(spec, "head")
    assert markers["head"][1][1] == pytest.approx(head_len, abs=1e-4)

    # Limbs are displaced along -Y by segment length (distal joint centres)
    for seg in ("upper_arm", "forearm", "hand", "thigh", "shank"):
        _, seg_len, _ = _seg(spec, seg)
        for side in ("l", "r"):
            m_name = f"{seg}_{side}"
            assert markers[m_name][1][1] == pytest.approx(-seg_len, abs=1e-4), (
                f"{m_name} Y offset does not match -{seg}.length"
            )
