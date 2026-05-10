//! Kinematics kernels.
//!
//! Parallel batch center-of-mass (COM) computation across segment positions.

use ndarray::Array2;
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use rayon::prelude::*;

/// Parallel batch center-of-mass computation.
///
/// Given segment positions `(n_frames, n_segments, 3)` flattened to
/// `(n_frames, n_segments * 3)` and segment masses `(n_segments,)`,
/// returns the whole-body COM trajectory `(n_frames, 3)`.
#[pyfunction]
pub fn com_batch<'py>(
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

// ---------------------------------------------------------------------------
// Pure-Rust unit tests (no Python interpreter required)
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use ndarray::{Array1, Array2};

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
        // 1 segment at (1,2,3) with mass 5 -> COM = (1,2,3)
        let pos = Array2::from_shape_vec((1, 3), vec![1.0, 2.0, 3.0]).unwrap();
        let masses = Array1::from_vec(vec![5.0]);
        let result = com_pure(&pos, &masses);
        assert!((result[[0, 0]] - 1.0).abs() < 1e-12);
        assert!((result[[0, 1]] - 2.0).abs() < 1e-12);
        assert!((result[[0, 2]] - 3.0).abs() < 1e-12);
    }

    #[test]
    fn test_com_two_segments() {
        // seg0 at (0,0,0) mass=1, seg1 at (4,6,8) mass=1 -> COM = (2,3,4)
        let pos = Array2::from_shape_vec((1, 6), vec![0.0, 0.0, 0.0, 4.0, 6.0, 8.0]).unwrap();
        let masses = Array1::from_vec(vec![1.0, 1.0]);
        let result = com_pure(&pos, &masses);
        assert!((result[[0, 0]] - 2.0).abs() < 1e-12);
        assert!((result[[0, 1]] - 3.0).abs() < 1e-12);
        assert!((result[[0, 2]] - 4.0).abs() < 1e-12);
    }

    #[test]
    fn test_com_weighted_average() {
        // seg0 at (0,0,0) mass=2, seg1 at (6,0,0) mass=1 -> COM = (2,0,0)
        let pos =
            Array2::from_shape_vec((1, 6), vec![0.0, 0.0, 0.0, 6.0, 0.0, 0.0]).unwrap();
        let masses = Array1::from_vec(vec![2.0, 1.0]);
        let result = com_pure(&pos, &masses);
        assert!((result[[0, 0]] - 2.0).abs() < 1e-12);
        assert!(result[[0, 1]].abs() < 1e-12);
        assert!(result[[0, 2]].abs() < 1e-12);
    }
}
