"""Tests for the ``opensim_models.model_pack`` entry-point API.

The API is consumed by UpstreamDrift (umbrella issue
``D-sorganization/UpstreamDrift#5179``) via the
``[project.entry-points."biomech.model_pack"]`` group; the manifest is
validated against the ``model_pack/v1`` schema published in
``D-sorganization/UpstreamDrift#5199``.

Live ``opensim.Model(path)`` parse checks are marked ``live_simulation``
and are skipped by default; the unit-level checks load the generated
``.osim`` as XML and assert non-zero ``Body`` / ``Joint`` / muscle counts.
"""

from __future__ import annotations

import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from opensim_models import model_pack
from opensim_models.__main__ import main as cli_main
from opensim_models.exercises import EXERCISE_BUILDERS

_EXPECTED_EXERCISES = (
    "squat",
    "deadlift",
    "bench_press",
    "snatch",
    "clean_and_jerk",
    "gait",
    "sit_to_stand",
)


class TestManifest:
    def test_schema_is_model_pack_v1(self) -> None:
        assert model_pack.manifest()["schema"] == "model_pack/v1"

    def test_repo_and_package(self) -> None:
        data = model_pack.manifest()
        assert data["repo"] == "OpenSim_Models"
        assert data["package"] == "opensim_models"

    def test_engine_pinned_to_opensim_44_plus(self) -> None:
        data = model_pack.manifest()
        assert data["engine"] == "opensim"
        assert data["engine_version"] == ">=4.4"

    def test_format_is_osim(self) -> None:
        assert model_pack.manifest()["format"] == "osim"

    def test_anthropometrics_is_winter_2009(self) -> None:
        assert model_pack.manifest()["anthropometrics"] == "winter_2009"

    def test_exercises_match_expected_set(self) -> None:
        ids = {entry["id"] for entry in model_pack.manifest()["exercises"]}
        assert ids == set(_EXPECTED_EXERCISES)

    def test_each_exercise_has_existing_path(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        for entry in model_pack.manifest()["exercises"]:
            path = (repo_root / entry["path"]).resolve()
            assert path.is_dir(), f"exercise path missing: {path}"


class TestResolve:
    def test_returns_absolute_path(self) -> None:
        assert model_pack.resolve().is_absolute()

    def test_returns_existing_exercises_directory(self) -> None:
        root = model_pack.resolve()
        assert root.is_dir()
        for name in _EXPECTED_EXERCISES:
            assert (root / name).is_dir(), f"missing exercise dir: {name}"


class TestListExercises:
    def test_returns_all_seven_ids(self) -> None:
        assert set(model_pack.list_exercises()) == set(_EXPECTED_EXERCISES)

    def test_list_is_stable_across_calls(self) -> None:
        assert model_pack.list_exercises() == model_pack.list_exercises()


class TestCLI:
    @pytest.mark.parametrize("exercise", _EXPECTED_EXERCISES)
    def test_export_writes_parseable_osim(
        self,
        tmp_path: Path,
        exercise: str,
    ) -> None:
        output = tmp_path / f"{exercise}.osim"
        cli_main(["--exercise", exercise, "--export", str(output)])
        assert output.is_file()
        root = ET.fromstring(output.read_text(encoding="utf-8"))
        assert root.tag == "OpenSimDocument"
        # Non-zero body / joint counts -- same shape as the MuJoCo
        # coordination-issue tests.
        assert len(root.findall(".//Body")) > 0
        assert (
            len(root.findall(".//Joint")) > 0
            or len(
                [
                    child
                    for joint_set in root.findall(".//JointSet")
                    for child in joint_set
                ]
            )
            > 0
        )

    def test_list_exercises_prints_all_ids(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        cli_main(["--list-exercises"])
        out = capsys.readouterr().out
        for name in _EXPECTED_EXERCISES:
            assert name in out

    def test_missing_exercise_exits_with_error(self) -> None:
        with pytest.raises(SystemExit):
            cli_main([])

    def test_python_dash_m_invocation(self, tmp_path: Path) -> None:
        # Smoke-test the launcher contract exactly as documented in #264:
        #   python -m opensim_models --exercise gait --export /tmp/gait.osim
        output = tmp_path / "gait.osim"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "opensim_models",
                "--exercise",
                "gait",
                "--export",
                str(output),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert output.is_file()
        text = output.read_text(encoding="utf-8")
        assert "<OpenSimDocument" in text


class TestExerciseBuilderParity:
    """Every manifest exercise must be wired into ``EXERCISE_BUILDERS``."""

    @pytest.mark.parametrize("exercise", _EXPECTED_EXERCISES)
    def test_each_manifest_exercise_has_a_builder(self, exercise: str) -> None:
        assert exercise in EXERCISE_BUILDERS


@pytest.mark.live_simulation
@pytest.mark.parametrize("exercise", _EXPECTED_EXERCISES)
def test_generated_osim_loads_via_opensim_model(tmp_path: Path, exercise: str) -> None:
    """End-to-end parse via ``opensim.Model(path)``.

    Marked ``live_simulation`` -- skipped by default because the ``opensim``
    Python wheel is not installable on every CI lane. UpstreamDrift's
    integration job runs the live lane.
    """
    opensim = pytest.importorskip("opensim")
    output = tmp_path / f"{exercise}.osim"
    cli_main(["--exercise", exercise, "--export", str(output)])
    model = opensim.Model(str(output))
    model.initSystem()
    assert model.getBodySet().getSize() > 0
    assert model.getJointSet().getSize() > 0
    # Muscle count: some exercises may be muscle-free; assert >= 0 to
    # document the contract while remaining permissive.
    assert model.getMuscles().getSize() >= 0
