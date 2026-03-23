# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email the maintainers with a description of the vulnerability.
3. Include steps to reproduce and any relevant details.

We will acknowledge receipt within 48 hours and aim to provide a fix or
mitigation within 7 days for critical issues.

## Security Measures

This project employs the following security practices:

- **Dependency scanning**: Dependabot monitors for known vulnerabilities.
- **pip-audit**: CI runs `pip-audit` to check for vulnerable packages.
- **Bandit**: Static analysis for common Python security issues.
- **Minimal dependencies**: Only `numpy` is required at runtime.
- **No network access**: Model generation is entirely offline.
- **No file system writes**: Unless explicitly requested via CLI `--output`.
