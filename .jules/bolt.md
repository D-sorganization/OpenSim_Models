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
## 2024-04-24 - Numpy dot vs native math for small fixed-size vectors
**Learning:** For small, fixed-size 3-element vectors in performance critical sections, `np.dot` with `np.asarray` is drastically slower than accessing the elements using native Python float casts and executing mathematical operations explicitly (`dx * dx + dy * dy + dz * dz`). The overhead of creating numpy objects heavily outweighs the raw C execution speed benefits of the numpy math library.
**Action:** When working with 3-element vectors for operations like computing the dot product in hot paths such as those in geometry and inertia calculators, use native Python element access and scalar math instead of numpy generic vector operations.
## 2024-05-18 - Fast path for NumPy Arrays in Contract Checks
**Learning:** Type-checking nested lists/tuples correctly is too error-prone for precondition checks (risk of allowing multi-dimensional inputs masquerading as 1D).
**Action:** When adding fast paths to `np.asarray()` conversion in hot code, only use `if type(arr) is np.ndarray:` to safely bypass overhead without risking regressions for list/tuple inputs.

## 2026-04-25 - Numpy Array Creation Overhead
**Learning:** In performance-critical functions that construct small, fixed-size matrices (like 3x3 rotation matrices), passing nested Python lists to `np.array()` (e.g., `np.array([[1, 0, 0], [0, c, -s], ...])`) introduces severe object allocation and type inference overhead inside numpy.
**Action:** Pre-allocate the array using `np.zeros((3, 3), dtype=float)` and assign the non-zero elements explicitly to reduce function overhead by 40-45%.## 2024-04-26 - Unrolling loops in hot path validators
**Learning:** In OpenSim model generators, postcondition checks (like `ensure_positive_definite_inertia`) are called heavily in inner loops. Using python loops over tuples (`for label, val in [("Ixx", ixx)...]`) creates significant allocation overhead (lists, tuples) and function call overhead (`_is_finite_positive`).
**Action:** Inline checks and unroll small loops manually for validation functions that live on the hot path to avoid list/tuple allocations.

## 2026-04-27 - Numpy Array Creation Overhead in Shape Validation
**Learning:** Checking the shape of Python collections (like `list` or `tuple`) by passing them to `np.asarray()` and checking `.shape` adds severe object allocation overhead (around 3-4x slower) in hot paths (such as `require_shape` checks).
**Action:** Implement a fast path in array validators that explicitly checks the `len()` of elements for simple 1D arrays (and verifies no sub-arrays exist) before falling back to `np.asarray()`.
## 2026-04-29 - Mathematical Operator Overhead in Hot Paths
**Learning:** In frequently called geometry construction functions, the Python exponentiation operator (`**2`) is measurably slower than simple multiplication (`x * x`).
**Action:** When working on geometry, inertia, or vector calculations in hot paths, expand squares into simple multiplications. Do NOT precalculate fractional constants (e.g. `1.0 / 12.0` to `0.08333333333333333`) because the Python AST compiler already performs constant folding at compile-time (and doing so manually hurts code readability without any performance gain).

## 2026-04-30 - Fast path for constant formatted strings in hot paths
**Learning:** In a codebase generating large structured text (like OpenSim XML configurations), formatting small float-based primitives repeatedly introduces severe bottlenecks. Zero vectors (`(0.0, 0.0, 0.0)`) are extremely common. Python's f-string formatting handles these by parsing the float format specifier over and over again.
**Action:** When working with frequently called formatting helpers for strings that are heavily skewed toward one or two constant values (e.g., zero translations/rotations), implement a fast path that checks for the exact values and returns a static string literal to avoid f-string overhead entirely.

## 2026-04-30 - String Formatting Overhead in Hot Paths
**Learning:** In very hot paths like OpenSim XML vector formatting (`vec3_str`, `vec6_str`), standard f-strings (`f"{x:.6f} {y:.6f}"`) incur significant parsing overhead compared to old-style `%` formatting (`"%.6f %.6f" % (x, y)`), likely due to the number of individual format components being resolved at runtime. `%f` formatting was benchmarked to be ~40% faster.
**Action:** When formatting basic numbers into strings in loops executed thousands of times (like model serialization), prefer `%` formatting over f-strings and add a `# noqa: UP031` comment to bypass Ruff's default preference.
## 2025-02-28 - Fast Path for Zero Vectors in XML Generation
**Learning:** In generating OpenSim XML models, rotation and translation vectors are very often identically zero, and the overhead of format interpolation (`"%.6f" %`) makes up a significant part of the hot-path latency. Bypassing string formatting with a simple equivalence check yields a 4-5x speedup.
**Action:** When working in hot string-building loops, consider fast-path logic for the most common static default values, returning pre-compiled string literals instead of dynamic evaluation.

## 2026-05-01 - Type Checking Overhead in Preconditions
**Learning:** Checking types using `isinstance(vec, (list, tuple))` introduces measurable overhead compared to explicit exact type checking (`type(vec) is list or type(vec) is tuple`) due to Python's MRO and subclass hierarchy resolution. In heavily hit precondition checks like `require_unit_vector`, avoiding `isinstance` yields a ~30% improvement in type checking speed.
**Action:** When performing type-checks in performance-critical execution paths to route behavior for basic Python types (like `list` or `tuple`), prefer exact checking with `type(x) is T` rather than `isinstance(x, T)`.

## 2026-05-11 - PyO3 numpy `into_pyarray` vs `into_pyarray_bound`
**Learning:** PyO3 `0.21` and `0.22` enforce the new Bound lifetimes and `into_pyarray_bound` over `into_pyarray` when translating ndarray types to Python. Using the deprecated functions on rust_core causes CI failures on strict checks like `cargo doc`.
**Action:** Always use `into_pyarray_bound` instead of `into_pyarray` for PyO3 0.21+ compatibility.

## 2024-05-18 - Exact type checking with `is` vs `in`
**Learning:** Checking for standard Python sequence types in high-frequency validation hot paths using `type(x) in (list, tuple, np.ndarray)` is significantly slower than unrolling and using exact identity checks `tx = type(x); if tx is list or tx is tuple or tx is np.ndarray:`. Additionally, unrolling element validation loops for known, common vector sizes (like length 3) avoids loop overhead and significantly improves performance.
**Action:** When creating fast paths for specific types (especially for small, fixed-size structures like 3-vectors), unroll loops and use exact identity checks (`is`) on `type(obj)` rather than `in` or `isinstance` for maximum performance in hot paths.

## 2026-05-22 - Redundant XML Parsing in Postconditions
**Learning:** During model building, the XML tree (`ET.Element`) is serialized to a string using `serialize_model(root)`. Calling `ET.fromstring()` on this newly serialized string immediately afterwards just to run postcondition checks introduces massive redundant parsing overhead, taking up to ~20% of the entire model generation time.
**Action:** When working with XML serialization and validation workflows, pass the existing `ET.Element` tree directly to the validation functions instead of validating the raw string output if you already have the DOM object in memory.
## 2024-05-19 - XML Scalar Float Formatting
**Learning:** In the hot path of generating OpenSim XML output, individual scalar floats (such as mass, coordinates, radii, friction) frequently default to `0.0`. Applying the same performance trick used for vector formatting—checking `if v == 0.0` to return `"0.000000"` directly and using `%.6f` instead of f-strings—yields a massive ~10x speedup for the common zero case (~36 ns vs ~447 ns per loop) without sacrificing readability when encapsulated in a helper function.
**Action:** Extract and reuse localized float formatting functions (e.g., `float_str(v: float) -> str`) to handle the formatting of single numerical properties consistently and efficiently across the module.

## 2024-05-25 - Fast Path np.ndarray checks with math.isfinite() and np.isfinite().all()
**Learning:** For small fixed-size numpy arrays (like length-3 vectors), explicitly unrolling the check using `math.isfinite(float(arr.flat[i]))` is ~7x faster than using `np.all(np.isfinite(arr))`. For general array sizes, using `np.isfinite(arr).all()` is ~1.6x faster than `np.all(np.isfinite(arr))` because it avoids the overhead of creating a new intermediate array structure for the result.
**Action:** Always prefer unrolling simple element-wise checks for hot-path fixed-size short arrays, and prefer `.all()` or `.any()` as methods on numpy array result objects rather than wrapping in `np.all()` or `np.any()`.

## 2024-05-28 - Fast Path Scalar Validation via Exact Type Checking
**Learning:** Exact type checking (`type(x) is float`) is significantly faster (~2x) than `isinstance(x, (float, int))` because it bypasses Method Resolution Order (MRO) overhead. However, `isinstance` is still needed as a fallback to correctly handle subclasses like numpy scalars (e.g. `np.float64`).
**Action:** In hot paths validating scalar numbers, always short-circuit with exact type checks (`type(x) is float or type(x) is int`) before falling back to `isinstance(x, (float, int))`.

## 2026-05-31 - Fast path for diagonal inertia matrices in XML generation
**Learning:** OpenSim Body inertia formatting often deals with diagonal matrices where the cross-terms (`ixy`, `ixz`, `iyz`) are strictly `0.0`. Standard string formatting loops or f-strings unnecessarily parse and format these zeros.
**Action:** In `add_body` or similar helpers generating inertia strings, add a fast path that checks `if inertia_xy == 0.0 and inertia_xz == 0.0 and inertia_yz == 0.0:` to return a partially pre-compiled string (e.g. `"... 0.000000 0.000000 0.000000"`). This bypasses formatting overhead for the cross-terms, yielding a measurable speedup.

## 2024-05-19 - Exact Type Checking overhead and Native Numpy Array items
**Learning:** For small NumPy arrays (like 3-vectors), `float(arr.flat[i])` or `float(arr[i])` is slower than using `arr.item(i)`, which retrieves the native Python scalar directly. Also, when checking sequence types in Python hot paths (like `require_shape`), a positive check (`tx is float or tx is int`) is both faster and safer than a negative exclusion list (`not (tx is list or tx is tuple or ...)`).
**Action:** When extracting scalar values from small NumPy arrays in hot paths, use `arr.item(i)` instead of indexing and casting with `float()`. Use explicit positive inclusion lists (e.g., `is float or is int`) instead of negative exclusion lists for type validation in hot paths.

## 2026-06-14 - XML Tree Traversal Batched Updating
**Learning:** `xml.etree.ElementTree.iter()` generates a new iterator that traverses the entire XML subtree every time it is called. When setting many defaults (like 10-15 coordinate values for an OpenSim model) individually, this results in an O(N^2) operation overhead because the tree is fully traversed for each coordinate.
**Action:** Always batch XML element updates. Create functions that accept a dictionary of target elements and update values, traversing the XML tree exactly once and maintaining a counter to short-circuit the loop early once all elements are found.

## 2026-06-14 - Test Configuration Modification Risks
**Learning:** Automatically removing unused dependencies or configuration flags (like `asyncio_mode` in pytest `addopts`) to silence local warnings can inadvertently break CI pipelines that rely on those flags in different environments.
**Action:** Never modify test runner configurations (like `pyproject.toml` `pytest.ini_options`) to silence warnings unless explicitly requested. Instead, bypass strict configuration checks locally (e.g. `pytest -o addopts=""`) and leave the repository configuration intact.

## 2024-05-29 - Fast path for small Python lists and tuples in validation
**Learning:** In high-frequency precondition checks (like `require_finite`), standard python lists and tuples suffer from iteration and internal type-checking overhead (checking for nested sequences in elements). For very common, small, fixed sizes (like 3-element and 6-element vectors), this overhead dominates execution time.
**Action:** Unroll checks for known list/tuple sequence lengths directly checking elements using explicit index access (e.g. `arr_len == 3` -> `math.isfinite(arr[0]) and math.isfinite(arr[1])...`) bypassing loop and dynamic type-checking overhead.

## 2024-05-18 - Exact type checking with `__class__` vs `type()`
**Learning:** Checking types using exact identity checks `val.__class__ is float` is significantly faster (~15-20%) than `type(val) is float` because it avoids the function call overhead of `type()`.
**Action:** When performing exact type checks in performance-critical execution paths (like `list`, `tuple`, `float`, `int`, `np.ndarray`), prefer exact checking with `x.__class__ is T` rather than `type(x) is T`.
