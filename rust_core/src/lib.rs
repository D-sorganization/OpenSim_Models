//! Rust accelerator for OpenSim Models.
//!
//! Provides parallel batch computation for inverse dynamics, center-of-mass,
//! and phase interpolation using Rayon for data parallelism and PyO3/NumPy
//! for seamless Python interop.
//!
//! The kernels are organised into focused submodules:
//!
//! * [`dynamics`]      - inverse dynamics batch kernel
//! * [`kinematics`]    - center-of-mass batch kernel
//! * [`interpolation`] - phase interpolation kernel
//!
//! This file is intentionally a thin public-API entrypoint: it declares the
//! submodules and assembles the PyO3 module. All computational logic lives in
//! the submodules so no single file exceeds the monolith threshold.

use pyo3::prelude::*;

pub mod dynamics;
pub mod interpolation;
pub mod kinematics;

pub use dynamics::inverse_dynamics_batch;
pub use interpolation::interpolate_phases_rs;
pub use kinematics::com_batch;

/// Python module definition.
#[pymodule]
fn opensim_models_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(inverse_dynamics_batch, m)?)?;
    m.add_function(wrap_pyfunction!(com_batch, m)?)?;
    m.add_function(wrap_pyfunction!(interpolate_phases_rs, m)?)?;
    Ok(())
}
