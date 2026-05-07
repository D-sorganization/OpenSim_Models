# Criterion G: Dependency Hygiene

**Repo:** OpenSim_Models
**Score:** 60/100
**Weight:** 8%
**Weighted Contribution:** 4.80

## Evidence

```json
{
  "req_lockfiles": 0,
  "req_files": 1
}
```

## Findings

### P1: [OpenSim_Models] No dependency lockfile

Generate lockfile (pip freeze --require-hashes, poetry lock, npm ci) for reproducible builds.
