# Contributing

## Setup

```bash
git clone <repo>
cd DBI-DB
cp .env.example .env   # fill in values
docker compose up -d
```

Backend: Python 3.11, install with `pip install -e ".[dev]"` inside the backend container or venv.
Frontend: Node 20, `npm install` in `frontend/`.

## Commits — Conventional Commits

```
feat: add query endpoint
fix(backend): handle empty result set
docs: update setup instructions
refactor: split retriever from chain
test: cover SQLite cache layer
chore: bump qdrant to 1.12
```

Scope is the module name (`backend`, `frontend`, `rag`, `docker`, `docs`).

## Code Style

- **Python**: ruff (lint + format). `ruff check . && ruff format .` before commit. Config in `pyproject.toml`.
- **TypeScript**: prettier + eslint. `npm run format` and `npm run lint`.

## Tests

- Backend: `pytest`. New code needs tests. Aim for ≥80% coverage on touched modules.
- Frontend: `npm test`. Component tests for new UI.
- Run `docker compose up -d` first so Qdrant/Redis are available.

## PRs

- Branch from `main`. One feature/fix per PR.
- CI must pass (lint, test, build-docker).
- Reference the issue: `Closes #123`.
- Squash-merge.