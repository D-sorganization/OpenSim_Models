"""Root conftest for pytest -- shared fixtures across all test modules.

Per Fleet Testing Standards §5, set thread-safety and headless env vars
before any heavy import. See:
https://github.com/D-sorganization/Repository_Management/blob/main/docs/FLEET_TESTING_STANDARDS.md
"""

from __future__ import annotations

import os

# C-extension thread safety. Many "xdist worker crashed" failures
# come from MKL/OpenBLAS forking under xdist. Pin to single-threaded
# for tests; production code can re-thread itself if it needs to.
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

# matplotlib headless backend, set before any matplotlib import.
os.environ.setdefault("MPLBACKEND", "Agg")

# Qt headless backend, for repos that import PyQt/PySide indirectly.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import xml.etree.ElementTree as ET  # noqa: E402

import pytest  # noqa: E402

from opensim_models.exercises.base import ExerciseConfig
from opensim_models.shared.barbell import BarbellSpec
from opensim_models.shared.body import BodyModelSpec


@pytest.fixture()
def default_body_spec() -> BodyModelSpec:
    """Standard 75 kg, 1.75 m body spec used throughout the test suite."""
    return BodyModelSpec()


@pytest.fixture()
def default_barbell_spec() -> BarbellSpec:
    """Standard men's Olympic barbell with default plate mass."""
    return BarbellSpec.mens_olympic()


@pytest.fixture()
def default_exercise_config(
    default_body_spec: BodyModelSpec,
    default_barbell_spec: BarbellSpec,
) -> ExerciseConfig:
    """Default ExerciseConfig wired with standard body and barbell specs."""
    return ExerciseConfig(
        body_spec=default_body_spec,
        barbell_spec=default_barbell_spec,
    )


@pytest.fixture()
def empty_jointset() -> ET.Element:
    """An empty JointSet XML element for testing joint helpers."""
    return ET.Element("JointSet")


@pytest.fixture()
def empty_bodyset() -> ET.Element:
    """An empty BodySet XML element for testing body helpers."""
    return ET.Element("BodySet")
