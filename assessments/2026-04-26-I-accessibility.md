# Criterion I: Accessibility

**Weight:** 6% | **Score:** 5.0/10 | **Grade:** D

## Evidence

- CLI entry point: `python -m opensim_models <exercise> [--output] [--mass] [--height] [--plates]`
- No GUI or web interface present
- Outputs `.osim` XML files for OpenSim
- No accessibility annotations or testing
- No screen reader support or ARIA labels (not applicable for CLI)

## Positive Findings

- CLI has help text and argument validation
- DbC validation with clear error messages

## Negative Findings

### P1-I001: No accessibility considerations for visualizations
- `src/opensim_models/visualization/plots.py`: matplotlib output
- No colorblind-safe palette or alternative text for plots

## Justification

Primarily a library/CLI tool, so accessibility scope is limited. No explicit accessibility measures beyond CLI help text.
