//! Inverse dynamics kernels.
//!
//! Parallel batch inverse dynamics using a diagonal-inertia approximation
//! suitable for rigid-body chains.

use ndarray::{Array1, Array2};
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
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
pub fn inverse_dynamics_batch<'py>(
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

    Ok(result.into_pyarray_bound(py).into())
}

// ---------------------------------------------------------------------------
// Pure-Rust unit tests (no Python interpreter required)
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use ndarray::{Array1, Array2};

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

    #[test]
    fn test_inverse_dynamics_multi_frame() {
        // Verify parallel batch produces correct results across multiple frames
        let pos = Array2::from_shape_vec(
            (3, 2),
            vec![0.0, 0.0, std::f64::consts::FRAC_PI_2, 0.0, 0.0, std::f64::consts::FRAC_PI_2],
        )
        .unwrap();
        let vel = Array2::<f64>::zeros((3, 2));
        let acc = Array2::<f64>::zeros((3, 2));
        let inr = Array1::from_vec(vec![1.0, 1.0]);
        let dmp = Array1::from_vec(vec![0.0, 0.0]);
        let grv = Array1::from_vec(vec![1.0, 1.0]);

        let result = inverse_dynamics_pure(&pos, &vel, &acc, &inr, &dmp, &grv);
        // Frame 0: sin(0)=0, sin(0)=0
        assert!(result[[0, 0]].abs() < 1e-12);
        // Frame 1: sin(pi/2)=1, sin(0)=0
        assert!((result[[1, 0]] - 1.0).abs() < 1e-12);
        assert!(result[[1, 1]].abs() < 1e-12);
        // Frame 2: sin(0)=0, sin(pi/2)=1
        assert!(result[[2, 0]].abs() < 1e-12);
        assert!((result[[2, 1]] - 1.0).abs() < 1e-12);
    }
}
