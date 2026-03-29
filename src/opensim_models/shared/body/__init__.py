"""Full-body musculoskeletal model for OpenSim.

Provides a simplified but anatomically grounded full-body model with
major body segments and joints suitable for barbell exercise simulation.
"""

from opensim_models.shared.body._segment_data import BodyModelSpec
from opensim_models.shared.body.body_model import create_full_body
from opensim_models.shared.body.foot_contact import add_foot_contact_spheres

__all__ = ["BodyModelSpec", "add_foot_contact_spheres", "create_full_body"]
