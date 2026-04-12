//! Phase interpolation kernels.
//!
//! Parallel linear interpolation of waypoint values over a normalised time grid.

use ndarray::{Array1, Array2, Axis};
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;
use rayon::prelude::*;

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
pub fn interpolate_phases_rs<'py>(
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

// ---------------------------------------------------------------------------
// Pure-Rust unit tests (no Python interpreter required)
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use ndarray::{Array1, Array2};

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

    #[test]
    fn test_interpolate_three_waypoints() {
        // 3 waypoints: 0->10->0 at t=0, 0.5, 1.0
        let tf = Array1::from_vec(vec![0.0, 0.5, 1.0]);
        let wv = Array2::from_shape_vec((3, 1), vec![0.0, 10.0, 0.0]).unwrap();
        let result = interpolate_pure(&tf, &wv, 5);
        // t=0.0 -> 0, t=0.25 -> 5, t=0.5 -> 10, t=0.75 -> 5, t=1.0 -> 0
        assert!((result[[0, 0]] - 0.0).abs() < 1e-10);
        assert!((result[[1, 0]] - 5.0).abs() < 1e-10);
        assert!((result[[2, 0]] - 10.0).abs() < 1e-10);
        assert!((result[[3, 0]] - 5.0).abs() < 1e-10);
        assert!((result[[4, 0]] - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_interpolate_multi_coord() {
        // 2 coords, 2 waypoints: coord0 goes 0->10, coord1 goes 10->0
        let tf = Array1::from_vec(vec![0.0, 1.0]);
        let wv = Array2::from_shape_vec((2, 2), vec![0.0, 10.0, 10.0, 0.0]).unwrap();
        let result = interpolate_pure(&tf, &wv, 3);
        // midpoint: coord0=5, coord1=5
        assert!((result[[1, 0]] - 5.0).abs() < 1e-10);
        assert!((result[[1, 1]] - 5.0).abs() < 1e-10);
    }
}
