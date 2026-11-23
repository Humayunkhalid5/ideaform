# Contributing to Ideaform

## Branches

| Branch | Purpose |
| --- | --- |
| `main` | Stable. Only receives merges from `dev` at the end of a phase. |
| `dev` | Integration branch. Every feature merges here first. |
| `feature/<short-name>` | One task per branch, cut from `dev` (e.g. `feature/project-crud`). |
| `fix/<short-name>` | Bug fixes, cut from `dev`. |

Never commit directly to `main`. Rebase or merge `dev` into your branch before opening
a pull request, and keep the branch's commits focused on the task it is named for.

## Pull requests

1. Open the PR against `dev`, not `main`.
2. One reviewer is required; the reviewer runs the checks below.
3. Squash-merge with a message matching the commit convention.
4. Delete the branch after merge.

## Commit messages

`<type>: <summary>` where type is one of `feat`, `fix`, `docs`, `refactor`, `test`,
`chore`. Example: `feat: add hybrid search`.

## Local setup

```bash
cp .env.example .env            # add GROQ_API_KEY (and TAVILY_API_KEY when needed)
docker compose up -d --build
curl -fsS localhost:8000/health/ready
```

## Secrets

- `.env` is git-ignored; it is the only place keys live. Never paste a key into a
  source file, a commit, a PR, an issue, or a screenshot.
- `.env.example` lists every required variable with empty or placeholder values.
- Rotate a key immediately if it is ever committed or shared; see the provider console.

## Checks before review

```bash
make health     # API liveness and readiness
make migrate    # Alembic upgrade on a clean database
make test       # pytest
```
