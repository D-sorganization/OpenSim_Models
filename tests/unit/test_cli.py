"""Tests for the OpenSim model generator CLI."""

from __future__ import annotations

import pytest

from opensim_models import __main__ as cli


class TestMain:
    def test_writes_default_output_for_barbell_exercise(self, tmp_path, monkeypatch):
        calls = []

        def fake_builder(**kwargs):
            calls.append(kwargs)
            return "<OpenSimDocument><Model name='bench_press' /></OpenSimDocument>"

        monkeypatch.chdir(tmp_path)
        monkeypatch.setitem(cli._BUILDERS, "bench_press", fake_builder)

        cli.main(
            ["bench_press", "--mass", "72.5", "--height", "1.82", "--plates", "12.5"]
        )

        assert (
            (tmp_path / "bench_press.osim")
            .read_text(encoding="utf-8")
            .startswith("<OpenSimDocument>")
        )
        assert calls == [
            {
                "body_mass": 72.5,
                "height": 1.82,
                "plate_mass_per_side": 12.5,
            }
        ]

    def test_writes_explicit_output_without_plates_for_gait(
        self, tmp_path, monkeypatch
    ):
        calls = []
        output_path = tmp_path / "nested" / "gait.osim"
        output_path.parent.mkdir()

        def fake_builder(**kwargs):
            calls.append(kwargs)
            return "<OpenSimDocument><Model name='gait' /></OpenSimDocument>"

        monkeypatch.setitem(cli._BUILDERS, "gait", fake_builder)

        cli.main(
            [
                "gait",
                "--output",
                str(output_path),
                "--mass",
                "65",
                "--height",
                "1.65",
                "--plates",
                "99",
                "--verbose",
            ]
        )

        assert output_path.read_text(encoding="utf-8").endswith("</OpenSimDocument>")
        assert calls == [{"body_mass": 65.0, "height": 1.65}]

    @pytest.mark.parametrize(
        ("args", "message"),
        [
            (["squat", "--mass", "0"], "--mass must be positive"),
            (["squat", "--height", "-1"], "--height must be positive"),
            (["squat", "--plates", "-0.1"], "--plates must be non-negative"),
        ],
    )
    def test_rejects_invalid_numeric_arguments(self, args, message, monkeypatch):
        def unexpected_builder(**kwargs):
            raise AssertionError("builder should not be called")

        monkeypatch.setitem(cli._BUILDERS, "squat", unexpected_builder)

        with pytest.raises(SystemExit, match=message):
            cli.main(args)

    def test_parser_lists_available_exercises(self):
        parser = cli._build_parser()

        exercise_action = next(
            action for action in parser._actions if action.dest == "exercise"
        )

        assert exercise_action.choices == sorted(cli._BUILDERS)
        assert "Generate OpenSim .osim models" in parser.description
