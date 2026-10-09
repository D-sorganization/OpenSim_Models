"""Centralised user-visible strings for OpenSim_Models.

All user-facing strings (log messages, exception messages, CLI output)
must be defined here. Hardcoding English strings in other modules is
considered a regression.

This module exists to make a future i18n migration trivial: replace the
constants with gettext lookups (e.g. ``_()``) without touching logic files.
"""

# CLI argument descriptions
CLI_DESCRIPTION = "Generate OpenSim .osim models for barbell exercises."
CLI_EXERCISE_HELP = "Exercise to generate a model for."
CLI_OUTPUT_HELP = "Output file path (default: <exercise>.osim in current directory)."
CLI_MASS_HELP = "Body mass in kg (default: 80)."
CLI_HEIGHT_HELP = "Body height in meters (default: 1.75)."
CLI_PLATES_HELP = "Plate mass per side in kg (default: 60)."
CLI_VERBOSE_HELP = "Enable debug logging."
CLI_EXPORT_HELP = "Export the generated .osim file to this path (alias of --output)."
CLI_LIST_EXERCISES_HELP = "Print the list of declared exercise IDs and exit."

# CLI validation errors
ERR_MASS_POSITIVE = "--mass must be positive, got {value}"
ERR_HEIGHT_POSITIVE = "--height must be positive, got {value}"
ERR_PLATES_NONNEGATIVE = "--plates must be non-negative, got {value}"

# Log messages
LOG_BUILDING_MODEL = "Building %s model"
LOG_MODEL_BUILT = "%s model built successfully"
LOG_WROTE_FILE = "Wrote %s"
LOG_GENERATED_FILE = "Generated %s (%d bytes)"

# Exception messages
ERR_UNKNOWN_EXERCISE = "Unknown exercise '{name}'. Available: {available}"
ERR_NUM_POINTS = "num_points must be >= 2, got {value}"
ERR_JOINT_NOT_FOUND = "Joint '{name}' not found in positions dict"
ERR_NO_JOINTS_TO_PLOT = "No joints to plot: positions dict is empty"
ERR_NO_JOINT_TARGETS = "Exercise '{name}' has no joint targets in phases"
ERR_DEADLIFT_FEASIBILITY = "Feasibility check failed for deadlift with mass={mass}, height={height}, plates={plates}"

# Model-pack manifest errors
ERR_MANIFEST_MISSING = "model_pack.yaml not found (searched: {paths})"
ERR_MODELS_ROOT_MISSING = "models_root directory does not exist: {path}"
ERR_EXERCISE_REQUIRED = (
    "an exercise must be specified via the positional argument or --exercise"
)

# Inverse Dynamics Tool errors
ERR_OPENSIM_NOT_INSTALLED = "OpenSim is not installed or could not be imported"
ERR_INVALID_MODEL = (
    "Model must be an opensim.Model instance or path to an .osim file, got {model!r}"
)
ERR_COORDINATES_FILE_NOT_FOUND = "Coordinates file not found: {path}"
ERR_EXTERNAL_LOADS_FILE_NOT_FOUND = "External loads file not found: {path}"
ERR_INVALID_TIME_RANGE = "time_range must be a tuple of (start_time, end_time) with start_time <= end_time, got {value}"
ERR_TIMES_REQUIRED = "times sequence is required when supplying in-memory coordinates"
ERR_TIMES_TOO_SHORT = (
    "times must have at least 6 points for spline evaluation, got {count}"
)
ERR_TIMES_NOT_INCREASING = "times must be strictly increasing"
ERR_COORDINATE_LENGTH_MISMATCH = (
    "Coordinate '{name}' length {length} does not match times length {expected}"
)
ERR_COORDINATE_NOT_IN_MODEL = "Coordinate '{name}' is not in the model"
ERR_NO_COORDINATES_SPECIFIED = (
    "Must specify coordinates_file or times to run inverse dynamics"
)
ERR_ID_TOOL_RUN_FAILED = "OpenSim InverseDynamicsTool execution failed"
ERR_LOWPASS_CUTOFF_FINITE = "lowpass_cutoff_frequency must be finite, got {value}"
