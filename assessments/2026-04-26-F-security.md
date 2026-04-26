# Criterion F: Security

**Weight:** 10% | **Score:** 7.0/10 | **Grade:** C

## Evidence

- `.pre-commit-config.yaml` includes gitleaks v8.18.2 for secrets scanning
- CI runs bandit security scan: `bandit -r src/ -ll -ii --format txt`
- CI runs pip-audit (with ignored CVEs)
- `AGENTS.md` explicitly states: "NEVER commit API keys, passwords, tokens"
- `.gitignore` excludes `.env`
- No hardcoded secrets found in source grep
- Dockerfile runs as non-root user (`athlete`, UID 1000)

## Positive Findings

- Multi-layer security scanning (gitleaks + bandit + pip-audit)
- AGENTS.md security directive for contributors
- Non-root container execution
- Environment file exclusion in .gitignore

## Negative Findings

### P1-F001: Multiple CVEs ignored in CI
- pip-audit step ignores 6 CVEs: CVE-2026-4539, CVE-2026-32274, CVE-2026-21883, CVE-2026-27205, CVE-2024-47081, CVE-2026-25645
- File: `.github/workflows/ci-standard.yml:75`

## Justification

Strong security tooling but the explicit CVE ignore list without documented risk acceptance reduces confidence. Non-root container and secrets scanning are positive.
