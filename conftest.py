"""Root conftest for pytest -- shared fixtures across all test modules."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

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
