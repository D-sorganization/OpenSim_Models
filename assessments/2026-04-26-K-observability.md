# Criterion K: Observability

**Weight:** 7% | **Score:** 5.0/10 | **Grade:** D

## Evidence

- Logging used throughout: `logging.getLogger(__name__)` in all exercise modules
- CLI has `--verbose` flag for debug logging
- CI uploads coverage artifacts
- No metrics export (Prometheus, OpenTelemetry, etc.)
- No structured logging (JSON format)
- No distributed tracing

## Positive Findings

- Consistent logging pattern across modules
- Debug mode available via CLI

## Negative Findings

### P1-K001: No metrics or telemetry system
- No performance counters, error rates, or usage metrics
- No integration with observability platforms

## Justification

Basic logging only. No metrics, tracing, or structured logs for production observability.
