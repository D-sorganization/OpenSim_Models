#!/usr/bin/env python3
"""Generate all five exercise models with default anthropometrics.

Usage:
    python3 examples/generate_all_models.py [--output-dir OUTPUT_DIR]

Creates one .osim file per exercise in the specified output directory
(defaults to current working directory).
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from opensim_models.exercises.bench_press.bench_press_model import (
    build_bench_press_model,
)
from opensim_models.exercises.clean_and_jerk.clean_and_jerk_model import (
    build_clean_and_jerk_model,
)
from opensim_models.exercises.deadlift.deadlift_model import build_deadlift_model
from opensim_models.exercises.snatch.snatch_model import build_snatch_model
from opensim_models.exercises.squat.squat_model import build_squat_model

logger = logging.getLogger(__name__)

_EXERCISES = {
    "squat": build_squat_model,
    "bench_press": build_bench_press_model,
    "deadlift": build_deadlift_model,
    "snatch": build_snatch_model,
    "clean_and_jerk": build_clean_and_jerk_model,
}


def main() -> None:
    """Generate all exercise models."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory to write .osim files (default: cwd)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(name)s %(levelname)s: %(message)s",
    )

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, builder in _EXERCISES.items():
        xml_str = builder()
        out_path = output_dir / f"{name}.osim"
        out_path.write_text(xml_str, encoding="utf-8")
        print(f"Generated {out_path} ({len(xml_str)} bytes)")

    print(f"\nAll {len(_EXERCISES)} models generated in {output_dir}")


if __name__ == "__main__":
    main()
