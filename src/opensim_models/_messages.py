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