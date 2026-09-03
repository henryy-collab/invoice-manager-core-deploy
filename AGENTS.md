# AGENTS.md

Compact repo guide. For the full session starter (config, workflow, architecture detail), see `project/docs/AGENTS.md`.

## Repo & remotes

Two packages wired by `pyproject.toml` (`where = ["local", "ui"]`):
- `local/invoice_parser/` — PyMuPDF PDF parser/renamer (CLI, `local/parse_and_rename.py`).
- `ui/invoice_ui/` — FastAPI web UI (`ui/web_ui.py`).

Git remotes:
- `origin` — source of truth (`henryy-collab/invoice-manager-core`).
- `glass` — deployment mirror (`FirstPage-Glass/invoice-manager-core`); Coolify auto-deploys its `master`. **Only push `glass master` on an explicit release**, never during normal development.
- `deploy` — Zeabur deploy repo (do not push during normal work).

## Branching

- Default branch is `master`. Branch off `master` for work using `feat/<slug>`, `fix/<slug>`, `docs/<slug>`, `ci/<slug>`. `master` itself is not pushed directly to `glass` except when releasing.

## Committing

- Use `gh` to commit and open PRs.
- Conventional prefixes: `feat:`, `fix:`, `docs:`, `ci:`, `refactor:`, `style:`.
- Do not commit unless explicitly asked.

## Always update docs (in the same branch/PR)

Docs are part of the feature, not an afterthought. When code changes behavior, config, or the user-facing workflow:
1. `docs/CHANGELOG.md` — add a dated entry.
2. `README.md` — high-level setup, data layout, deployment notes.
3. `local/README.md` — config examples, features, usage.
4. `docs/DEPLOYMENT.md` — when deploy/env/secrets/release behavior changes.
5. `docs/SERVICE_ACCOUNT_SETUP.md` — when Google Drive/Sheets/auth changes.
6. `project/docs/AGENTS.md` — keep the session guide current with architecture/config changes.

If docs would mislead before the code, the docs need updating.

## Working with subagents

Break large tasks into small, independent parts instead of one big prompt. Each part must be simple enough to implement, verify, and review on its own.

- Split by responsibility, not by file. Each part should have one job (e.g. "add the report column", "update the NocoDB mapping", "write tests for the parser plumbing").
- Each part must be independently verifiable: give it its own test(s) or a concrete check (a test suite, `--dry-run`, a curl to an endpoint).
- Subagents start with fresh context. When delegating a part, pack the prompt with everything needed: file paths, existing patterns/conventions, the exact acceptance criteria, and the verify command. Do not assume they can infer the repo layout.
- Have subagents implement only that part, run its verification, and return a short report (files changed, tests run, results). The orchestrating session keeps the overall flow, cross-cutting docs, and all commits.
- Re-run the full test suites after integrating any subagent output (`cd local; python -m pytest`, `cd ..\ui; python -m pytest`). Never accept a part that breaks its suite.
- Keep parts focused; avoid subagents making doc changes or refactors outside their assigned scope.

## Commands (Windows PowerShell)

- Install: `python -m pip install -e .`
- Run UI: `python ui\web_ui.py` → http://127.0.0.1:8000
- Run CLI: `python local\parse_and_rename.py --dry-run` (preview without touching files)
- Tests: run **both** suites:
  ```
  cd local; python -m pytest
  cd ..\ui; python -m pytest
  ```
- No lint/format/typecheck commands are configured.

## Gotchas

- No code comments unless asked.
- `local/local_config.json` is machine-specific and gitignored — never commit it. Copy `local/local_config.example.json` to create it. Relative paths resolve from the project root (the dir containing `.git`).
- Runtime data lives in gitignored `local/data/` (incoming, outgoing, archive, logs, reports, state) and is created automatically on startup.
- Config is driven by a `document_types` registry; `default_document_type` is used when no classifier matches.
- After UI changes, bump the cache-busting query string (`?v=`) in `ui/static/index.html`; users must hard-refresh (`Ctrl+F5`).
- `project/` is archived reference — it may reference old repo paths, the old external `invoice-manager-data/` folder, or files that no longer exist. Verify against current core layout before acting on anything there.