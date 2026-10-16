"""Ground-contact policy shared by every exercise model (OpenSim_Models#472)."""

from opensim_models.shared.contact.policy import (
    CONTACT_STIFFNESS,
    FOOT_CONTACT_POINTS,
    FOOT_SPHERE_RADIUS,
    GROUND_FRICTION,
    foot_contact_offsets,
    foot_sphere_names,
    static_normal_force,
)

__all__ = [
    "CONTACT_STIFFNESS",
    "FOOT_CONTACT_POINTS",
    "FOOT_SPHERE_RADIUS",
    "GROUND_FRICTION",
    "foot_contact_offsets",
    "foot_sphere_names",
    "static_normal_force",
]
