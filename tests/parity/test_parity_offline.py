"""Engine-free parity checks: run on every Python version, OpenSim or not.

These exercise the vendored bundle with this pack's own data (generated XML,
alias tables, ledger and manifest) so that the 3.10 lane, which has no opensim
wheel, still verifies the parity contract.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises, manifest
from opensim_models.shared.parity._canonical import assemble, conformance
from opensim_models.shared.parity.fingerprint import (
    COORDINATE_ALIASES,
    SEGMENT_ALIASES,
)

STD = conformance.load_standard()
LEDGER = Path(conformance.__file__).parents[1] / "parity_divergences.json"
ROOT_COORDINATE_PREFIX = "pelvis_"


def _generated_coordinates(exercise: str) -> set[str]:
    root = ET.fromstring(EXERCISE_BUILDERS[exercise]())
    names = {c.get("name", "") for c in root.iter("Coordinate")}
    return {n for n in names if not n.startswith(ROOT_COORDINATE_PREFIX)}


@pytest.mark.parametrize("exercise", list_exercises())
def test_aliases_map_generated_coordinates_onto_canonical_set(exercise: str) -> None:
    canonical = {COORDINATE_ALIASES.get(n, n) for n in _generated_coordinates(exercise)}
    assert canonical == set(conformance.expected_coordinates(STD))


def test_ledger_is_valid_and_cites_issues() -> None:
    ledger = conformance.load_ledger(LEDGER)
    unexpected, stale = conformance.reconcile_all({}, ledger)
    assert unexpected == {}
    # No exercise was checked, so scoped entries cannot be judged stale.
    assert stale == [
        key for key, e in sorted(ledger["divergences"].items()) if "exercises" not in e
    ]
    # Issue references (#N or URL) are validated by the canonical reconcile_all.
    for entry in ledger["divergences"].values():
        assert set(entry.get("exercises", [])) <= set(list_exercises())


def test_capabilities_parse_from_pack_manifest() -> None:
    caps = assemble.capabilities_from_manifest(manifest(), STD)
    assert caps["load_in_engine"] == "full"


def test_failed_load_is_a_single_load_divergence() -> None:
    fp = assemble.failed_fingerprint("opensim", "4.6", "squat", RuntimeError("x"))
    assert [d.key for d in conformance.check_fingerprint(fp, STD)] == ["load_in_engine"]


def test_y_up_measurements_assemble_into_a_conforming_fingerprint() -> None:
    """The adapter's frame and aliases produce a clean fingerprint when the
    engine reports standard values (engine-native names, Y-up vectors)."""
    inverse = {v: k for k, v in COORDINATE_ALIASES.items()}
    limits = {
        inverse.get(name, name): lim
        for name, lim in conformance.expected_coordinates(STD).items()
    }
    g = STD["frame"]["gravity_mps2"]
    fp = assemble.assemble_fingerprint(
        engine="opensim",
        engine_version="offline",
        exercise="gait",
        std=STD,
        root_joint="free",
        gravity_engine=(0.0, -g, 0.0),
        segment_masses_kg=conformance.expected_segments(STD),
        coordinate_limits_rad=limits,
        segment_origins_engine_m={"pelvis": (0.0, 1.0, 0.0), "head": (0, 1.6, 0)},
        capabilities=assemble.capabilities_from_manifest(manifest(), STD),
        coordinate_aliases=COORDINATE_ALIASES,
        segment_aliases=SEGMENT_ALIASES,
    )
    assert conformance.check_fingerprint(fp, STD) == []
    assert math.isclose(fp["segment_origins_neutral_m"]["head"][2], 0.6)
