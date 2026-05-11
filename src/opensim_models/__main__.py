"""CLI entry point: python -m opensim_models <exercise> [--output FILE] [--mass KG] [--height M] [--plates KG].

Also supports the UpstreamDrift launcher contract
(``D-sorganization/UpstreamDrift#5179``) via ``--exercise <name>``,
``--export <path>``, and ``--list-exercises``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from opensim_models._messages import (
    CLI_DESCRIPTION,
    CLI_EXERCISE_HELP,
    CLI_EXPORT_HELP,
    CLI_HEIGHT_HELP,
    CLI_LIST_EXERCISES_HELP,
    CLI_MASS_HELP,
    CLI_OUTPUT_HELP,
    CLI_PLATES_HELP,
    CLI_VERBOSE_HELP,
    ERR_EXERCISE_REQUIRED,
    ERR_HEIGHT_POSITIVE,
    ERR_MASS_POSITIVE,
    ERR_PLATES_NONNEGATIVE,
    LOG_GENERATED_FILE,
    LOG_WROTE_FILE,
)
from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models.model_pack import list_exercises as _list_exercises

logger = logging.getLogger(__name__)

_BUILDERS = EXERCISE_BUILDERS
_NO_BARBELL_EXERCISES = {"gait", "sit_to_stand"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opensim_models",
        description=CLI_DESCRIPTION,
    )
    # Positional is kept for back-compat with the pre-UpstreamDrift CLI.
    # The new launcher contract uses ``--exercise`` instead.
    parser.add_argument(
        "exercise",
        nargs="?",
        choices=sorted(_BUILDERS),
        help=CLI_EXERCISE_HELP,
    )
    parser.add_argument(
        "--exercise",
        dest="exercise_flag",
        choices=sorted(_BUILDERS),
        default=None,
        help=CLI_EXERCISE_HELP,
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=CLI_OUTPUT_HELP,
    )
    parser.add_argument(
        "--export",
        dest="export",
        type=Path,
        default=None,
        help=CLI_EXPORT_HELP,
    )
    parser.add_argument(
        "--list-exercises",
        action="store_true",
        help=CLI_LIST_EXERCISES_HELP,
    )
    parser.add_argument("--mass", type=float, default=80.0, help=CLI_MASS_HELP)
    parser.add_argument(
        "--height",
        type=float,
        default=1.75,
        help=CLI_HEIGHT_HELP,
    )
    parser.add_argument(
        "--plates",
        type=float,
        default=60.0,
        help=CLI_PLATES_HELP,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help=CLI_VERBOSE_HELP)
    return parser


def _resolve_exercise(args: argparse.Namespace) -> str:
    exercise = args.exercise_flag or args.exercise
    if not exercise:
        raise SystemExit(ERR_EXERCISE_REQUIRED)
    return exercise


def _resolve_output_path(args: argparse.Namespace, exercise: str) -> Path:
    # ``--export`` (UpstreamDrift contract) takes precedence over ``--output``
    # (legacy flag) which in turn beats the default ``<exercise>.osim``.
    return args.export or args.output or Path(f"{exercise}.osim")


def _validate_numeric_args(args: argparse.Namespace) -> None:
    if args.mass <= 0:
        sys.exit(ERR_MASS_POSITIVE.format(value=args.mass))
    if args.height <= 0:
        sys.exit(ERR_HEIGHT_POSITIVE.format(value=args.height))
    if args.plates < 0:
        sys.exit(ERR_PLATES_NONNEGATIVE.format(value=args.plates))


def main(argv: list[str] | None = None) -> None:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)

    if args.list_exercises:
        for name in _list_exercises():
            sys.stdout.write(f"{name}\n")
        return

    exercise = _resolve_exercise(args)
    _validate_numeric_args(args)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    builder = _BUILDERS[exercise]
    if exercise in _NO_BARBELL_EXERCISES:
        xml_str = builder(body_mass=args.mass, height=args.height)
    else:
        xml_str = builder(
            body_mass=args.mass,
            height=args.height,
            plate_mass_per_side=args.plates,
        )

    output_path = _resolve_output_path(args, exercise)
    output_path.write_text(xml_str, encoding="utf-8")
    logger.info(LOG_WROTE_FILE, output_path)
    logger.info(LOG_GENERATED_FILE, output_path, len(xml_str))


if __name__ == "__main__":
    main(sys.argv[1:])
