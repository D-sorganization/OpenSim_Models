"""Full-body musculoskeletal model for OpenSim.

Provides a simplified but anatomically grounded full-body model with
major body segments and joints suitable for barbell exercise simulation.
"""

from opensim_models.shared.body.body_model import (
    BodyModelSpec,
    add_foot_contact_spheres,
    create_full_body,
)

__all__ = ["BodyModelSpec", "add_foot_contact_spheres", "create_full_body"]
