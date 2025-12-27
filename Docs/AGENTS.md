# Documentation

Project documentation files.

## Documentation Files

| File | Purpose |
|------|---------|
| `PROJECT_OVERVIEW.md` | Complete project context, workflows, models |
| `DEVELOPMENT.md` | Local dev setup, testing guide |
| `DEPLOYMENT.md` | Railway deployment instructions |
| `ARCHITECTURE_PATTERNS.md` | DRY patterns: decorators, managers, middleware |

## Standards

- All new documentation goes in `Docs/`, not project root
- Use markdown format
- Include code examples where relevant
- Keep README.md at root minimal - point to `Docs/`

## When to Update

| Change | Update |
|--------|--------|
| New model or workflow | `PROJECT_OVERVIEW.md` |
| New test patterns | `DEVELOPMENT.md` |
| New DRY pattern | `ARCHITECTURE_PATTERNS.md` |
| Deployment changes | `DEPLOYMENT.md` |

## Quick Reference

For architecture patterns (decorators, managers, middleware), see:
[ARCHITECTURE_PATTERNS.md](ARCHITECTURE_PATTERNS.md)

