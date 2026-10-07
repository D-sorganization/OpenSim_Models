"""Engine-free tests for the vendored ``ledger`` and ``assemble`` modules.

Covers the validation and error branches the offline pack tests do not reach,
so the 3.10 lane (no opensim wheel) still exercises the whole bundle.
Refs D-sorganization/Repository_Management#2011.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from opensim_models.shared.parity._canonical import assemble, conformance, ledger

STD = conformance.load_standard()
SCHEMA = ledger.LEDGER_SCHEMA


@dataclass(frozen=True)
class _Div:
    key: str


def _ledger(**entries: dict[str, Any]) -> dict[str, Any]:
    return {"schema": SCHEMA, "divergences": entries}


# --- ledger -----------------------------------------------------------------


def test_load_ledger_missing_file_is_empty(tmp_path: Path) -> None:
    assert ledger.load_ledger(tmp_path / "nope.json") == {
        "schema": SCHEMA,
        "divergences": {},
    }


def test_load_ledger_reads_json(tmp_path: Path) -> None:
    path = tmp_path / "l.json"
    path.write_text(json.dumps(_ledger(a={"issue": "#1"})), encoding="utf-8")
    assert ledger.load_ledger(path)["divergences"] == {"a": {"issue": "#1"}}


def test_wrong_schema_rejected() -> None:
    with pytest.raises(ValueError, match="schema"):
        ledger.reconcile([], {"schema": "other", "divergences": {}})


@pytest.mark.parametrize(
    "entry",
    [{}, {"issue": "no reference"}, "not a dict", {"issue": 7}],
)
def test_entry_must_cite_an_issue(entry: Any) -> None:
    with pytest.raises(ValueError, match="must cite an issue"):
        ledger.reconcile([], _ledger(a=entry))


@pytest.mark.parametrize("scope", [[], "squat", [""], [1]])
def test_exercises_scope_must_be_non_empty_name_list(scope: Any) -> None:
    with pytest.raises(ValueError, match="exercises must list names"):
        ledger.reconcile([], _ledger(a={"issue": "#1", "exercises": scope}))


def test_reconcile_splits_unexpected_and_stale_with_wildcards() -> None:
    led = _ledger(**{"mass.*": {"issue": "#1"}, "gone": {"issue": "#2"}})
    divs = [_Div("mass.torso"), _Div("limit.knee")]
    unexpected, stale = ledger.reconcile(divs, led)
    assert unexpected == [_Div("limit.knee")]
    assert stale == ["gone"]


def test_scoped_entry_only_absorbs_its_exercise() -> None:
    led = _ledger(k={"issue": "#1", "exercises": ["squat"]})
    assert ledger.reconcile([_Div("k")], led, "squat") == ([], [])
    unexpected, stale = ledger.reconcile([_Div("k")], led, "gait")
    assert unexpected == [_Div("k")] and stale == ["k"]
    assert ledger.reconcile([_Div("k")], led)[0] == [_Div("k")]


def test_reconcile_all_reports_unexpected_per_exercise() -> None:
    led = _ledger(k={"issue": "#1"})
    unexpected, stale = ledger.reconcile_all(
        {"squat": [_Div("k"), _Div("x")], "gait": [_Div("k")]}, led
    )
    assert unexpected == {"squat": [_Div("x")]}
    assert stale == []


def test_reconcile_all_stale_scoped_entry_names_unused_members() -> None:
    led = _ledger(k={"issue": "#1", "exercises": ["squat", "gait", "bench"]})
    # squat uses it; gait was checked and does not; bench was never checked.
    _, stale = ledger.reconcile_all({"squat": [_Div("k")], "gait": []}, led)
    assert stale == ["k@gait"]
    _, stale = ledger.reconcile_all({"squat": [], "gait": [], "bench": []}, led)
    assert stale == ["k"]


# --- assemble ---------------------------------------------------------------


def _manifest(level: str = "full") -> dict[str, Any]:
    keys = STD["capabilities"]["keys"]
    return {"capabilities": {k: {"level": level} for k in keys}}


def test_capabilities_parse_all_standard_keys() -> None:
    caps = assemble.capabilities_from_manifest(_manifest("partial"), STD)
    assert set(caps) == set(STD["capabilities"]["keys"])
    assert set(caps.values()) == {"partial"}


def test_capabilities_reject_missing_extra_and_bad_level() -> None:
    short = _manifest()
    short["capabilities"].popitem()
    with pytest.raises(ValueError, match="missing"):
        assemble.capabilities_from_manifest(short, STD)
    extra = _manifest()
    extra["capabilities"]["warp_drive"] = {"level": "full"}
    with pytest.raises(ValueError, match="unexpected"):
        assemble.capabilities_from_manifest(extra, STD)
    with pytest.raises(ValueError, match="not in"):
        assemble.capabilities_from_manifest(_manifest("bogus"), STD)


def _assemble(**overrides: Any) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "engine": "opensim",
        "engine_version": "t",
        "exercise": "gait",
        "std": STD,
        "root_joint": "free",
        "gravity_engine": (0.0, -9.80665, 0.0),
        "segment_masses_kg": {"pelvis": 10.0, "barbell": 20.0},
        "coordinate_limits_rad": {"c": (-1.0, 1.0)},
        "segment_origins_engine_m": {"pelvis": (1, 1, 1), "torso": (1, 1.5, 1)},
        "capabilities": {},
    }
    return assemble.assemble_fingerprint(**{**kwargs, **overrides})


def test_assemble_rebases_on_pelvis_drops_non_human_and_rotates_frame() -> None:
    fp = _assemble()
    assert fp["segment_origins_neutral_m"]["torso"] == pytest.approx([0, 0, 0.5])
    assert list(fp["segments"]) == ["pelvis"]  # barbell dropped
    assert fp["body_mass_kg"] == pytest.approx(10.0)
    assert fp["gravity_canonical"] == pytest.approx([0, 0, -9.80665])
    assert "coordinate_axes" not in fp


def test_assemble_expresses_origins_in_pelvis_frame_and_poses() -> None:
    quarter = [(0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)]  # about Y
    fp = _assemble(
        pelvis_rotation_engine=quarter,
        segment_origins_test_poses_engine_m={
            "p": {"pelvis": (0, 0, 0), "torso": (1, 0, 0)}
        },
        coordinate_axes_engine={"a": (0.0, 2.0, 0.0)},
    )
    assert fp["segment_origins_neutral_m"]["torso"] == pytest.approx([0, 0, 0.5])
    assert fp["segment_origins_test_poses_m"]["p"]["torso"] == pytest.approx([0, -1, 0])
    assert fp["coordinate_axes"]["a"] == pytest.approx([0, 0, 1])


def test_assemble_rejects_alias_collision_and_core_extras() -> None:
    with pytest.raises(ValueError, match="alias collision"):
        _assemble(
            coordinate_limits_rad={"a": (0, 1), "b": (0, 1)},
            coordinate_aliases={"a": "x", "b": "x"},
        )
    with pytest.raises(ValueError, match="core key"):
        _assemble(extras={"engine": "hacked"})
    assert _assemble(extras={"note": 1})["note"] == 1


def test_assemble_rejects_non_finite_and_zero_axis() -> None:
    with pytest.raises(ValueError, match="finite"):
        _assemble(segment_masses_kg={"pelvis": math.nan})
    with pytest.raises(ValueError, match="non-zero"):
        _assemble(coordinate_axes_engine={"a": (0.0, 0.0, 0.0)})
    with pytest.raises(ValueError, match="finite"):
        _assemble(coordinate_axes_engine={"a": (math.inf, 0.0, 0.0)})


def test_failed_fingerprint_records_error() -> None:
    fp = assemble.failed_fingerprint("opensim", "4", "gait", KeyError("k"))
    assert fp["loaded_in_engine"] is False
    assert fp["load_error"].startswith("KeyError")


def test_cli_writes_fingerprints_and_rejects_unknown_exercise(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def fn(exercise: str) -> dict[str, Any]:
        return {"exercise": exercise}

    out = tmp_path / "out"
    rc = assemble.run_fingerprint_cli(["--all", "--out", str(out)], fn, ["a", "b"], "e")
    assert rc == 0
    assert json.loads((out / "e_b.json").read_text()) == {"exercise": "b"}
    bad = assemble.run_fingerprint_cli(
        ["--exercise", "z", "--out", str(out)], fn, ["a"], "e"
    )
    assert bad == 2
    assert "unknown exercise" in caplog.text
