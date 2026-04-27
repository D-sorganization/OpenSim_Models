"""CLI entry point: python -m opensim_models <exercise> [--output FILE] [--mass KG] [--height M] [--plates KG]."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from opensim_models.exercises import EXERCISE_BUILDERS
from opensim_models._messages import (
    CLI_DESCRIPTION,
    CLI_EXERCISE_HELP,
    CLI_OUTPUT_HELP,
    CLI_MASS_HELP,
    CLI_HEIGHT_HELP,
    CLI_PLATES_HELP,
    CLI_VERBOSE_HELP,
    ERR_MASS_POSITIVE,
    ERR_HEIGHT_POSITIVE,
    ERR_PLATES_NONNEGATIVE,
    LOG_WROTE_FILE,
    LOG_GENERATED_FILE,
)

logger = logging.getLogger(__name__)

_BUILDERS = EXERCISE_BUILDERS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="opensim_models",
        description=CLI_DESCRIPTION,
    )
    parser.add_argument(
        "exercise",
        choices=sorted(_BUILDERS),
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
        "--mass", type=float, default=80.0, help=CLI_MASS_HELP
    )
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
    parser.add_argument(
        "--verbose", "-v", action="store_true", help=CLI_VERBOSE_HELP
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the CLI."""
    args = _build_parser().parse_args(argv)

    # DbC: validate numeric arguments before constructing any model objects
    if args.mass <= 0:
        sys.exit(ERR_MASS_POSITIVE.format(value=args.mass))
    if args.height <= 0:
        sys.exit(ERR_HEIGHT_POSITIVE.format(value=args.height))
    if args.plates < 0:
        sys.exit(ERR_PLATES_NONNEGATIVE.format(value=args.plates))

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    builder = _BUILDERS[args.exercise]
    # Gait and sit-to-stand models don't accept plate_mass_per_side
    _NO_BARBELL_EXERCISES = {"gait", "sit_to_stand"}
    if args.exercise in _NO_BARBELL_EXERCISES:
        xml_str = builder(body_mass=args.mass, height=args.height)
    else:
        xml_str = builder(
            body_mass=args.mass,
            height=args.height,
            plate_mass_per_side=args.plates,
        )

    output_path = args.output or Path(f"{args.exercise}.osim")
    output_path.write_text(xml_str, encoding="utf-8")
    logger.info(LOG_WROTE_FILE, output_path)
    logger.info(LOG_GENERATED_FILE, output_path, len(xml_str))


if __name__ == "__main__":
    main(sys.argv[1:])
