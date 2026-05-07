# OpenSim_Models — Comprehensive A-O Health Assessment

**Date:** 2026-05-07
**Branch:** main
**HEAD:** `c37af9f2c90d383804eb69c151f97b35afc259f0`
**Owner/Repo:** D-sorganization/OpenSim_Models
**Source LOC:** 4641
**Test LOC:** 3869
**Code Files:** 125
**Branch Protection:** No

## Scores

| Criterion | Name | Score | Weight | Weighted |
|-----------|------|-------|--------|----------|
| A | Project Organization | 67 | 5% | 3.35 |
| B | Documentation | 93 | 8% | 7.44 |
| C | Testing | 75 | 12% | 9.00 |
| D | Error Handling | 98.2 | 10% | 9.82 |
| E | Performance | 70 | 7% | 4.90 |
| F | Code Quality | 90 | 10% | 9.00 |
| G | Dependency Hygiene | 60 | 8% | 4.80 |
| H | Security | 95 | 10% | 9.50 |
| I | Configuration Management | 100 | 6% | 6.00 |
| J | Observability | 55 | 7% | 3.85 |
| K | Maintenance Debt | 91.0 | 7% | 6.37 |
| L | CI/CD | 75 | 8% | 6.00 |
| M | Deployment | 70 | 5% | 3.50 |
| N | Legal & Compliance | 95 | 4% | 3.80 |
| O | Agentic Usability | 90 | 3% | 2.70 |
| **Total** | | | | **90.03** |

## Findings Summary

- **P0 (Critical):** 0
- **P1 (High):** 3
- **P2 (Medium):** 0

### P1 Findings

- **[A]** [OpenSim_Models] Top-level repository clutter (14 files)
- **[G]** [OpenSim_Models] No dependency lockfile
- **[L]** [OpenSim_Models] No branch protection on main


## Full Evidence

```json
{
  "repo": "OpenSim_Models",
  "branch": "main",
  "head_sha": "c37af9f2c90d383804eb69c151f97b35afc259f0",
  "head_date": "2026-04-29",
  "owner_repo": "D-sorganization/OpenSim_Models",
  "A": {
    "src_files": 53,
    "test_files": 44,
    "manifests": 1,
    "gitignore_lines": 42,
    "has_readme": 1,
    "clutter_files": 14
  },
  "B": {
    "readme_lines": 85,
    "readme_headers": 16,
    "docs_files": 3,
    "md_files": 8
  },
  "C": {
    "test_py": 44,
    "test_rs": 0,
    "src_py": 53,
    "src_rs": 0,
    "test_total": 44,
    "src_total": 53,
    "has_coverage": 1,
    "has_pytest_config": 1
  },
  "D": {
    "bare_except": 0,
    "except_exception": 0,
    "noqa_suppressions": 18
  },
  "E": {
    "benchmark_files": 0,
    "cache_decorators": 0
  },
  "F": {
    "todo_fixme": 0,
    "duplicate_risk": 0
  },
  "G": {
    "req_lockfiles": 0,
    "req_files": 1
  },
  "H": {
    "secrets_raw": 0,
    "bandit_cfg": 0,
    "security_md": 1
  },
  "I": {
    "env_example": 1,
    "config_files": 2
  },
  "J": {
    "logging_refs": 26,
    "metrics_refs": 1
  },
  "K": {
    "suppressions": 18,
    "todo_total": 0
  },
  "L": {
    "workflow_files": 5,
    "precommit_config": 1
  },
  "M": {
    "dockerfile": 1,
    "compose_files": 0
  },
  "N": {
    "license": 1,
    "copyright_headers": 0,
    "contributing": 1
  },
  "O": {
    "claude_md": 1,
    "agents_md": 1,
    "claude_lines": 68,
    "agents_lines": 48
  },
  "code_files": 125,
  "src_loc": 4641,
  "test_loc": 3869,
  "branch_protection": false
}
```