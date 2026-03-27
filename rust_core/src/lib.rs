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

    // --- Input validation ---
    if vel.shape() != pos.shape() {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "velocities shape {:?} does not match positions shape {:?}",
            vel.shape(),
            pos.shape()
        )));
    }
    if acc.shape() != pos.shape() {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "accelerations shape {:?} does not match positions shape {:?}",
            acc.shape(),
            pos.shape()
        )));
    }
    if inr.len() != n_dof {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "inertias length {} does not match n_dof {}",
            inr.len(),
            n_dof
        )));
    }
    if dmp.len() != n_dof {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "damping length {} does not match n_dof {}",
            dmp.len(),
            n_dof
        )));
    }
    if grv.len() != n_dof {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "gravity_terms length {} does not match n_dof {}",
            grv.len(),
            n_dof
        )));
    }

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
    let n_cols = pos.shape()[1];
    let n_segments = masses.len();

    // --- Input validation ---
    if n_cols != n_segments * 3 {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "segment_positions has {} columns but expected {} (n_segments={} * 3)",
            n_cols,
            n_segments * 3,
            n_segments
        )));
    }

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

    // --- Input validation ---
    if tf.len() != wv.shape()[0] {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "time_fractions length {} does not match waypoint_values rows {}",
            tf.len(),
            wv.shape()[0]
        )));
    }
    if num_points == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "num_points must be >= 1",
        ));
    }

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

// ---------------------------------------------------------------------------
// Pure-Rust unit tests (no Python interpreter required)
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;
    use ndarray::{Array1, Array2};

    // ---- inverse_dynamics helpers (pure Rust, mirrors the pyfunction logic) ----

    fn inverse_dynamics_pure(
        pos: &Array2<f64>,
        vel: &Array2<f64>,
        acc: &Array2<f64>,
        inr: &Array1<f64>,
        dmp: &Array1<f64>,
        grv: &Array1<f64>,
    ) -> Array2<f64> {
        let n_frames = pos.shape()[0];
        let n_dof = pos.shape()[1];
        assert_eq!(vel.shape(), pos.shape());
        assert_eq!(acc.shape(), pos.shape());
        assert_eq!(inr.len(), n_dof);
        assert_eq!(dmp.len(), n_dof);
        assert_eq!(grv.len(), n_dof);

        let mut result = Array2::<f64>::zeros((n_frames, n_dof));
        for i in 0..n_frames {
            for j in 0..n_dof {
                result[[i, j]] =
                    inr[j] * acc[[i, j]] + dmp[j] * vel[[i, j]] + grv[j] * pos[[i, j]].sin();
            }
        }
        result
    }

    #[test]
    fn test_inverse_dynamics_zeros() {
        let pos = Array2::<f64>::zeros((4, 3));
        let vel = Array2::<f64>::zeros((4, 3));
        let acc = Array2::<f64>::zeros((4, 3));
        let inr = Array1::from_vec(vec![1.0, 2.0, 3.0]);
        let dmp = Array1::from_vec(vec![0.1, 0.2, 0.3]);
        let grv = Array1::from_vec(vec![9.8, 9.8, 9.8]);

        let result = inverse_dynamics_pure(&pos, &vel, &acc, &inr, &dmp, &grv);
        // sin(0) = 0 so all outputs should be zero
        for val in result.iter() {
            assert!(val.abs() < 1e-12, "expected zero, got {}", val);
        }
    }

    #[test]
    fn test_inverse_dynamics_identity() {
        let pos = Array2::from_shape_vec((1, 2), vec![1.0, 0.0]).unwrap();
        let vel = Array2::from_shape_vec((1, 2), vec![2.0, 3.0]).unwrap();
        let acc = Array2::from_shape_vec((1, 2), vec![4.0, 5.0]).unwrap();
        let inr = Array1::from_vec(vec![1.0, 1.0]);
        let dmp = Array1::from_vec(vec![1.0, 1.0]);
        let grv = Array1::from_vec(vec![1.0, 1.0]);

        let result = inverse_dynamics_pure(&pos, &vel, &acc, &inr, &dmp, &grv);
        // tau[0] = 1*4 + 1*2 + 1*sin(1) = 6 + sin(1)
        let expected_0 = 4.0 + 2.0 + 1.0_f64.sin();
        assert!((result[[0, 0]] - expected_0).abs() < 1e-10);
        // tau[1] = 1*5 + 1*3 + 1*sin(0) = 8
        assert!((result[[0, 1]] - 8.0).abs() < 1e-10);
    }

    // ---- COM helpers ----

    fn com_pure(pos: &Array2<f64>, masses: &Array1<f64>) -> Array2<f64> {
        let n_frames = pos.shape()[0];
        let n_segments = masses.len();
        assert_eq!(pos.shape()[1], n_segments * 3);
        let total_mass: f64 = masses.iter().sum();

        let mut result = Array2::<f64>::zeros((n_frames, 3));
        for i in 0..n_frames {
            for s in 0..n_segments {
                for ax in 0..3 {
                    result[[i, ax]] += masses[s] * pos[[i, s * 3 + ax]];
                }
            }
            if total_mass > 0.0 {
                for ax in 0..3 {
                    result[[i, ax]] /= total_mass;
                }
            }
        }
        result
    }

    #[test]
    fn test_com_single_segment() {
        // 1 segment at (1,2,3) with mass 5 → COM = (1,2,3)
        let pos = Array2::from_shape_vec((1, 3), vec![1.0, 2.0, 3.0]).unwrap();
        let masses = Array1::from_vec(vec![5.0]);
        let result = com_pure(&pos, &masses);
        assert!((result[[0, 0]] - 1.0).abs() < 1e-12);
        assert!((result[[0, 1]] - 2.0).abs() < 1e-12);
        assert!((result[[0, 2]] - 3.0).abs() < 1e-12);
    }

    #[test]
    fn test_com_two_segments() {
        // seg0 at (0,0,0) mass=1, seg1 at (4,6,8) mass=1 → COM = (2,3,4)
        let pos = Array2::from_shape_vec((1, 6), vec![0.0, 0.0, 0.0, 4.0, 6.0, 8.0]).unwrap();
        let masses = Array1::from_vec(vec![1.0, 1.0]);
        let result = com_pure(&pos, &masses);
        assert!((result[[0, 0]] - 2.0).abs() < 1e-12);
        assert!((result[[0, 1]] - 3.0).abs() < 1e-12);
        assert!((result[[0, 2]] - 4.0).abs() < 1e-12);
    }

    // ---- Interpolation helpers ----

    fn interpolate_pure(tf: &Array1<f64>, wv: &Array2<f64>, num_points: usize) -> Array2<f64> {
        assert_eq!(tf.len(), wv.shape()[0]);
        assert!(num_points >= 1);
        let n_coords = wv.shape()[1];
        let dt = if num_points > 1 {
            1.0 / (num_points - 1) as f64
        } else {
            0.0
        };
        let mut result = Array2::<f64>::zeros((num_points, n_coords));
        for c in 0..n_coords {
            for k in 0..num_points {
                let t = k as f64 * dt;
                let mut lo = 0;
                for w in 0..tf.len() {
                    if tf[w] <= t {
                        lo = w;
                    }
                }
                let hi = (lo + 1).min(tf.len() - 1);
                if lo == hi {
                    result[[k, c]] = wv[[lo, c]];
                } else {
                    let frac = (t - tf[lo]) / (tf[hi] - tf[lo]);
                    result[[k, c]] = wv[[lo, c]] + frac * (wv[[hi, c]] - wv[[lo, c]]);
                }
            }
        }
        result
    }

    #[test]
    fn test_interpolate_two_waypoints() {
        let tf = Array1::from_vec(vec![0.0, 1.0]);
        let wv = Array2::from_shape_vec((2, 1), vec![0.0, 10.0]).unwrap();
        let result = interpolate_pure(&tf, &wv, 11);
        // Should linearly interpolate 0..10
        for k in 0..11 {
            let expected = k as f64;
            assert!(
                (result[[k, 0]] - expected).abs() < 1e-10,
                "at k={}: got {}, expected {}",
                k,
                result[[k, 0]],
                expected
            );
        }
    }

    #[test]
    fn test_interpolate_single_point() {
        let tf = Array1::from_vec(vec![0.0, 1.0]);
        let wv = Array2::from_shape_vec((2, 1), vec![5.0, 15.0]).unwrap();
        let result = interpolate_pure(&tf, &wv, 1);
        assert!((result[[0, 0]] - 5.0).abs() < 1e-10);
    }
}
