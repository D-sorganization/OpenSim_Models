## 2025-02-20 - Fast-Path Fallbacks with Exceptions
**Learning:** When adding exact-type fast-paths inside a `try...except` block, duplicating the slow-path fallback logic (e.g., converting to numpy arrays and generating precise Error messages) reduces maintainability.
**Action:** Instead of repeating the slow-path logic inside the fast-path's `else` blocks, explicitly `raise TypeError` to cleanly drop into the existing `except` block. This keeps the fast-path code lean while perfectly preserving existing error behavior.

## 2025-02-20 - Function Call Overhead vs. Code Reuse
**Learning:** Inlining simple mathematical checks (like `math.isfinite(x) and x > 0`) is significantly faster than wrapping them in a private helper function (`_is_finite_positive`). For validations called thousands of times during model generation, the function call overhead dominates the actual computation time.
**Action:** Inline simple, one-line mathematical conditions in high-frequency hot-paths rather than relying on private helper functions.
