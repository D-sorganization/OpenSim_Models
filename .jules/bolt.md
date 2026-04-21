## 2026-04-21 - [Fast-Path Preconditions for Scalars]
**Learning:** Frequent runtime type coercion from scalar floats/ints to NumPy arrays in preconditions (like `np.asarray` combined with `np.all(np.isfinite(...))`) creates a measurable performance bottleneck during repetitive geometry or model building calculations.
**Action:** Always add a fast-path for scalar values (using `isinstance(..., (int, float))` and built-ins like `math.isfinite()`) in frequently called numerical preconditions before falling back to NumPy array processing.
