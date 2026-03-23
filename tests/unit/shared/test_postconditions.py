"""Tests for postcondition checks."""

import pytest

from opensim_models.shared.contracts.postconditions import (
    ensure_positive_definite_inertia,
    ensure_positive_mass,
    ensure_valid_xml,
)


class TestEnsureValidXml:
    def test_accepts_valid_xml(self):
        root = ensure_valid_xml("<root><child/></root>")
        assert root.tag == "root"

    def test_rejects_malformed(self):
        with pytest.raises(ValueError, match="not well-formed"):
            ensure_valid_xml("<root><unclosed>")


class TestEnsurePositiveMass:
    def test_accepts_positive(self):
        ensure_positive_mass(1.0, "body")

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="not positive"):
            ensure_positive_mass(0.0, "body")

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="not positive"):
            ensure_positive_mass(-5.0, "body")


class TestEnsurePositiveDefiniteInertia:
    def test_accepts_valid_inertia(self):
        ensure_positive_definite_inertia(1.0, 1.0, 1.0, "body")

    def test_rejects_zero_component(self):
        with pytest.raises(ValueError, match="not positive"):
            ensure_positive_definite_inertia(0.0, 1.0, 1.0, "body")

    def test_rejects_triangle_inequality_violation(self):
        with pytest.raises(ValueError, match="triangle inequality"):
            ensure_positive_definite_inertia(0.1, 0.1, 100.0, "body")
