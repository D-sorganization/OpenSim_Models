# Criterion M: Data Handling

**Weight:** 5% | **Score:** 6.0/10 | **Grade:** D

## Evidence

- XML output generation for OpenSim models
- Input validation via DbC preconditions/postconditions
- No database or persistent storage
- No PII handling (biomechanical data only)
- No data retention policy visible

## Positive Findings

- DbC validation on all inputs
- Clean XML generation helpers

## Negative Findings

### P2-M001: No data validation schema
- XML output not validated against OpenSim XSD
- No schema enforcement in tests

## Justification

Simple data flow (inputs → model → XML). Missing schema validation is the primary gap.
