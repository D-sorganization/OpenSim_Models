## 2026-04-21 - Numpy Overhead on Scalars
**Learning:** In a codebase making extensive use of physics properties, `numpy.asarray` and universal functions like `numpy.isfinite` have significant overhead when called on scalar values (floats/ints). This became a bottleneck in core geometry construction functions (e.g. `cylinder_inertia`) that run thousands of times.
**Action:** When validating mathematical inputs via design-by-contract preconditions, implement a fast-path for native Python scalars using the `math` module (e.g., `math.isfinite()`) before falling back to `numpy` for arrays.
## 2026-04-22 - Precondition Function Overhead
**Learning:** Inlining `math.isfinite` in frequently called precondition checks (`require_positive`, `require_non_negative`) avoids function call overhead and prevents falling back to slower numpy paths when passing lists of scalars (as in `require_in_range`).
**Action:** When working with scalar validation guards that run in hot paths, avoid wrapping scalars in lists to use generic array-validation functions. Inline `math.isfinite` directly.

## 2026-04-22 - List Creation Overhead in Preconditions
**Learning:** Passing a dynamically created list `[value, low, high]` to a validation function (like `require_finite`) that converts it to a numpy array introduces severe overhead for simple scalar checks.
**Action:** When validating multiple scalar bounds, avoid intermediate list creation and use `math.isfinite()` on each scalar directly using a combined boolean expression.

## 2024-06-12 - Avoid array conversion overhead for simple list/tuple 3D vector norms
**Learning:** For typical 3-element Python inputs (`list`, `tuple`) and even `np.ndarray`, calculating magnitudes or norms using `np.linalg.norm(np.asarray(x))` creates significant object conversion overhead relative to the calculation itself in hot paths like `require_unit_vector`.
**Action:** Use native Python `math.hypot(x[0], x[1], x[2])` for operations on fixed-size small vectors whenever possible for major latency savings (up to 10x faster for standard Python lists/tuples). Use type fast-paths.

## 2024-06-13 - Native Python Math vs NumPy for Fixed Small Arrays
**Learning:** For small fixed-size 3D vector operations (like calculating the square of magnitudes during parallel axis shifts), using `numpy.asarray` and `numpy.dot` introduces significant object conversion overhead (up to ~7x slower for list/tuple inputs, and ~3x slower for existing `numpy` arrays).
**Action:** When working with typical 3-element Python coordinate vectors or displacements, unpack the elements, cast directly to `float`, and compute using native Python scalar arithmetic (`d_sq = dx*dx + dy*dy + dz*dz`) instead of using `numpy` helper methods.
