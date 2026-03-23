# AGENTS.md

## Agent Personas & Directives

**Audience:** Authoritative guide for AI agents working in this repository.

**Core Mission:**
- Write high-quality, maintainable, and secure code
- Adhere to project architectural and stylistic standards
- Follow TDD (Red/Green/Refactor), DbC, DRY, and Law of Demeter

## Safety & Security
- NEVER commit API keys, passwords, tokens
- Use .env files for secrets
- Review all code for security vulnerabilities

## Python Coding Standards
- Use logging module, not print()
- No wildcard imports
- Catch specific exceptions
- Use type hints
- Use ruff for formatting and linting

## Design Principles
- **TDD**: Write failing test first, make it pass, refactor
- **DbC**: Validate all inputs with preconditions, check outputs with postconditions
- **DRY**: Single source of truth for all logic
- **Law of Demeter**: Only talk to immediate collaborators
- **Small Functions**: Each function has a single purpose
- **No Monoliths**: Keep files under 300 lines

## Physics Engine: OpenSim
- Model format: `.osim` (OpenSim XML)
- Coordinate convention: Y-up
- Gravity: (0, -9.80665, 0)
- Bodies, Joints, and Forces defined in OpenSim XML schema
- Tests validate XML structure without requiring OpenSim installation

## Testing
- pytest with coverage >= 80%
- Property-based testing with hypothesis where appropriate
- Unit tests for all public functions
- Integration tests for model building

## Git Workflow
- Conventional Commits (feat:, fix:, docs:, test:, refactor:, chore:)
- Branch naming: feat/description, fix/description
- PRs must pass CI before merge
