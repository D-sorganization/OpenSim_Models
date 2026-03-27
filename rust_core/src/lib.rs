//! Rust accelerator for OpenSim Models.
//!
//! Provides parallel batch computation for inverse dynamics, center-of-mass,
//! and phase interpolation using Rayon for data parallelism and PyO3/NumPy
//! for seamless Python interop.

use ndarray::{Array1, Array2, Axis};
use numpy::{IntoPyArray, PyArray1, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use rayon::prelude::*;

/// Parallel batch inverse dynamics.
///
/// Given position, velocity, and acceleration arrays (each `n_frames x n_dof`),
/// computes generalised forces using the Newton-Euler recursive formulation
/// simplified for rigid-body chains: `tau = M * qddot + C(q, qdot) + G(q)`.
///
/// For this initial implementation we use a diagonal-inertia approximation
/// where each DOF has an effective inertia, damping, and gravity term.
///
/// # Arguments
/// * `positions`     - (n_frames, n_dof) joint positions in radians
/// * `velocities`    - (n_frames, n_dof) joint velocities in rad/s
/// * `accelerations` - (n_frames, n_dof) joint accelerations in rad/s^2
/// * `inertias`      - (n_dof,) effective rotational inertia per DOF
/// * `damping`       - (n_dof,) viscous damping coefficient per DOF
/// * `gravity_terms` - (n_dof,) gravity torque scale per DOF
#[pyfunction]
fn inverse_dynamics_batch<'py>(
    py: Python<'py>,
    positions: PyReadonlyArray2<'py, f64>,
    velocities: PyReadonlyArray2<'py, f64>,
    accelerations: PyReadonlyArray2<'py, f64>,
    inertias: PyReadonlyArray1<'py, f64>,
    damping: PyReadonlyArray1<'py, f64>,
    gravity_terms: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let pos = positions.as_array();
    let vel = velocities.as_array();
    let acc = accelerations.as_array();
    let inr = inertias.as_array();
    let dmp = damping.as_array();
    let grv = gravity_terms.as_array();

    let n_frames = pos.shape()[0];
    let n_dof = pos.shape()[1];

    // Compute each frame in parallel
    let rows: Vec<Array1<f64>> = (0..n_frames)
        .into_par_iter()
        .map(|i| {
            let mut tau = Array1::<f64>::zeros(n_dof);
            for j in 0..n_dof {
                tau[j] = inr[j] * acc[[i, j]]
                    + dmp[j] * vel[[i, j]]
                    + grv[j] * pos[[i, j]].sin();
            }
            tau
        })
        .collect();

    // Stack rows into (n_frames, n_dof)
    let mut result = Array2::<f64>::zeros((n_frames, n_dof));
    for (i, row) in rows.iter().enumerate() {
        result.row_mut(i).assign(row);
    }

    Ok(result.into_pyarray(py).into())
}

/// Parallel batch center-of-mass computation.
///
/// Given segment positions `(n_frames, n_segments, 3)` flattened to
/// `(n_frames, n_segments * 3)` and segment masses `(n_segments,)`,
/// returns the whole-body COM trajectory `(n_frames, 3)`.
#[pyfunction]
fn com_batch<'py>(
    py: Python<'py>,
    segment_positions: PyReadonlyArray2<'py, f64>,
    segment_masses: PyReadonlyArray1<'py, f64>,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let pos = segment_positions.as_array();
    let masses = segment_masses.as_array();
    let n_frames = pos.shape()[0];
    let n_segments = masses.len();
    let total_mass: f64 = masses.iter().sum();

    let rows: Vec<[f64; 3]> = (0..n_frames)
        .into_par_iter()
        .map(|i| {
            let mut com = [0.0_f64; 3];
            for s in 0..n_segments {
                for ax in 0..3 {
                    com[ax] += masses[s] * pos[[i, s * 3 + ax]];
                }
            }
            if total_mass > 0.0 {
                for ax in 0..3 {
                    com[ax] /= total_mass;
                }
            }
            com
        })
        .collect();

    let mut result = Array2::<f64>::zeros((n_frames, 3));
    for (i, com) in rows.iter().enumerate() {
        for ax in 0..3 {
            result[[i, ax]] = com[ax];
        }
    }

    Ok(result.into_pyarray(py).into())
}

/// Parallel phase interpolation.
///
/// Linearly interpolates waypoint values over a normalised time grid,
/// processing each coordinate column in parallel.
///
/// # Arguments
/// * `time_fractions` - (n_waypoints,) strictly increasing values in [0, 1]
/// * `waypoint_values` - (n_waypoints, n_coords) target values at each waypoint
/// * `num_points` - number of output time-steps
#[pyfunction]
fn interpolate_phases_rs<'py>(
    py: Python<'py>,
    time_fractions: PyReadonlyArray1<'py, f64>,
    waypoint_values: PyReadonlyArray2<'py, f64>,
    num_points: usize,
) -> PyResult<Bound<'py, PyArray2<f64>>> {
    let tf = time_fractions.as_array();
    let wv = waypoint_values.as_array();
    let n_coords = wv.shape()[1];

    // Build output time grid
    let dt = if num_points > 1 {
        1.0 / (num_points - 1) as f64
    } else {
        0.0
    };

    // Interpolate each coordinate in parallel
    let columns: Vec<Array1<f64>> = (0..n_coords)
        .into_par_iter()
        .map(|c| {
            let col = wv.index_axis(Axis(1), c);
            let mut out = Array1::<f64>::zeros(num_points);
            for k in 0..num_points {
                let t = k as f64 * dt;
                // Find bounding waypoints
                let mut lo = 0;
                for w in 0..tf.len() {
                    if tf[w] <= t {
                        lo = w;
                    }
                }
                let hi = (lo + 1).min(tf.len() - 1);
                if lo == hi {
                    out[k] = col[lo];
                } else {
                    let frac = (t - tf[lo]) / (tf[hi] - tf[lo]);
                    out[k] = col[lo] + frac * (col[hi] - col[lo]);
                }
            }
            out
        })
        .collect();

    let mut result = Array2::<f64>::zeros((num_points, n_coords));
    for (c, col) in columns.iter().enumerate() {
        result.column_mut(c).assign(col);
    }

    Ok(result.into_pyarray(py).into())
}

/// Python module definition.
#[pymodule]
fn opensim_models_core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(inverse_dynamics_batch, m)?)?;
    m.add_function(wrap_pyfunction!(com_batch, m)?)?;
    m.add_function(wrap_pyfunction!(interpolate_phases_rs, m)?)?;
    Ok(())
}
