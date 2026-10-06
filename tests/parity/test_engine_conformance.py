"""Real-engine conformance: every exercise loads in OpenSim and matches the standard."""

from __future__ import annotations

import hashlib
import importlib.resources
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises, manifest
from opensim_models.shared.parity._canonical import conformance
from opensim_models.shared.parity.fingerprint import fingerprint

needs_opensim = pytest.mark.skipif(
    sys.version_info < (3, 11),
    reason="the opensim pip wheel is published for CPython 3.11+ only",
)

EXERCISES = list_exercises()
CANONICAL = Path(conformance.__file__).parent
LEDGER = (
    Path(__file__).parents[2]
    / "src/opensim_models/shared/parity"
    / ("parity_divergences.json")
)
STD = conformance.load_standard()


def _expected_counts(osim_path: Path) -> tuple[int, int, int]:
    """Return (bodies, joints, coordinates) the generator intended."""
    model = ET.parse(osim_path).getroot().find("Model")
    assert model is not None
    bodies = len(list(model.iter("Body")))
    joints = sum(
        1 for js in model.iter("JointSet") for j in js.iter() if j.tag.endswith("Joint")
    )
    coords = len(list(model.iter("Coordinate")))
    return bodies, joints, coords


@needs_opensim
@pytest.mark.parametrize("exercise", EXERCISES)
def test_exercise_loads_in_opensim_with_expected_counts(
    tmp_path: Path, exercise: str
) -> None:
    import opensim

    path = tmp_path / f"{exercise}.osim"
    path.write_text(EXERCISE_BUILDERS[exercise](), encoding="utf-8")
    n_bodies, n_joints, n_coords = _expected_counts(path)
    model = opensim.Model(str(path))
    state = model.initSystem()
    assert model.getBodySet().getSize() == n_bodies >= 15
    assert model.getJointSet().getSize() == n_joints >= 15
    assert model.getCoordinateSet().getSize() == n_coords >= 28
    assert model.getForceSet().getSize() >= 8
    assert state is not None


@needs_opensim
@pytest.mark.parametrize("exercise", EXERCISES)
def test_fingerprint_has_no_unexpected_divergence(exercise: str) -> None:
    fp = fingerprint(exercise)
    assert fp["loaded_in_engine"], fp["load_error"]
    divs = conformance.check_fingerprint(fp, STD)
    ledger = conformance.load_ledger(LEDGER)
    unexpected, _ = conformance.reconcile(divs, ledger, exercise=exercise)
    assert not unexpected, [(d.key, d.expected, d.measured) for d in unexpected]


@needs_opensim
def test_divergence_ledger_has_no_stale_entries() -> None:
    by_exercise = {
        ex: conformance.check_fingerprint(fingerprint(ex), STD) for ex in EXERCISES
    }
    _, stale = conformance.reconcile_all(by_exercise, conformance.load_ledger(LEDGER))
    assert not stale, stale


@needs_opensim
def test_fingerprint_reports_canonical_names_and_frame() -> None:
    fp = fingerprint("squat")
    assert fp["schema"] == conformance.FINGERPRINT_SCHEMA
    assert set(fp["coordinates"]) == set(conformance.expected_coordinates(STD))
    assert set(fp["segments"]) == set(conformance.expected_segments(STD))
    assert fp["gravity_canonical"] == pytest.approx([0.0, 0.0, -9.80665])
    assert fp["segment_origins_neutral_m"]["pelvis"] == [0.0, 0.0, 0.0]
    # Standing: feet are below the pelvis in the canonical Z-up frame.
    assert fp["segment_origins_neutral_m"]["foot_l"][2] < -0.5


@needs_opensim
def test_fingerprint_rejects_unknown_exercise() -> None:
    with pytest.raises(ValueError, match="unknown exercise"):
        fingerprint("not_an_exercise")


def test_vendored_bundle_matches_manifest() -> None:
    files = json.loads((CANONICAL / "MANIFEST.json").read_text())["files"]
    assert files, "MANIFEST.json lists no files"
    for name, digest in files.items():
        actual = hashlib.sha256((CANONICAL / name).read_bytes()).hexdigest()
        assert actual == digest, f"vendored {name} was edited locally"


def test_standard_json_ships_as_package_data() -> None:
    pkg = importlib.resources.files("opensim_models.shared.parity._canonical")
    assert pkg.joinpath("biomech_parity_standard.json").is_file()


def test_capabilities_block_matches_standard() -> None:
    caps = manifest()["capabilities"]
    spec = STD["capabilities"]
    assert list(caps) == spec["keys"]
    root = Path(__file__).parents[2]
    for key, entry in caps.items():
        assert entry["level"] in spec["levels"], key
        if entry["evidence"] is not None:
            assert (root / entry["evidence"]).exists(), key
        else:
            assert entry["level"] == "none", f"{key}: evidence required"


@needs_opensim
@pytest.mark.parametrize("exercise", ["squat", "bench_press", "sit_to_stand"])
def test_fingerprint_reports_every_coordinate_axis(exercise: str) -> None:
    """Repository_Management#2011: axes are measured in OpenSim, not assumed."""
    from opensim_models.shared.parity._canonical import kinematics

    fp = fingerprint(exercise)
    assert set(fp["coordinate_axes"]) == set(kinematics.expected_axes(STD))
    assert kinematics.check_axes(fp, STD) == []
    assert kinematics.check_sides(fp, STD) == []
