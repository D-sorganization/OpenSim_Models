"""Barbell model generation for OpenSim.

Provides factory functions to create standard Olympic barbell bodies
with correct mass, geometry, and inertia properties.
"""

from opensim_models.shared.barbell.barbell_model import (
    BarbellSpec,
    create_barbell_bodies,
)

__all__ = ["BarbellSpec", "create_barbell_bodies"]
