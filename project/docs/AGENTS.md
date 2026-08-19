# Agent Session Starter

## Active project
- Repo: `C:\Users\Henry Yau\Apps\invoice-manager-core`
- GitHub: https://github.com/henryy-collab/invoice-manager-core
- Default branch: `master`
- Note: the original `invoice-manager` repo is deprecated. Continue all work here.

## Keeping this file up to date

`AGENTS.md` is the source of truth for the current repo state. When any of the following change, update this file in the same PR/commit:

- **Workflow or tab names/buttons**: update the “Current runtime flow” steps and any related labels.
- **Config fields, paths, or defaults**: update “Active config pointers” and any config examples.
- **New known issues or cache behavior**: update “Known quirks”.
- **Patterns for new features/config/frontend/backend**: update “Notes for future work”.
- **Archived docs, scripts or service files**: update the “Legacy references warning” and “Quick reference” lists.
- **Report columns or sheet behavior**: update the Write info to Report bullet in “Current runtime flow”.
- **This safe-word section or the safe word itself**: keep it current.
- **Documentation files outside `project/`**: when `README.md`, `local/README.md`, `docs/CHANGELOG.md`, `docs/DEPLOYMENT.md`, or `docs/SERVICE_ACCOUNT_SETUP.md` are updated, reflect the key points here so this file remains the single source of truth for agents.

## Always keep documentation up to date

Whenever code changes affect behavior, configuration, or the user-facing workflow, update the relevant documentation in the same branch:

1. **`docs/CHANGELOG.md`** — add a dated entry describing the change.
2. **`local/README.md`** — update config examples, feature descriptions, and usage instructions.
3. **`README.md`** — update high-level setup, data layout, deployment notes, and notes.
4. **`docs/SERVICE_ACCOUNT_SETUP.md`** — update if Google Drive/Sheets configuration, paths, or authentication behavior changes.
5. **`docs/DEPLOYMENT.md`** — update if Coolify setup, environment variables, secrets, or the release workflow change.
6. **`project/docs/AGENTS.md`** — keep this starter current with the latest architecture, config pointers, and conventions.

Treat documentation as part of the feature, not an afterthought. If a change would confuse someone reading the docs before the code, the docs need updating.

## Safe word

The safe word for this project is `SAFEWORD`. The agent must include it at the end of every response. If a response does not end with `SAFEWORD`, the session may have lost this context and a fresh session should be started.

---

## What this project is
A self-contained system for processing Google invoice PDFs:
- `local/` — Python PDF parser and renamer (CLI).
- `ui/` — FastAPI web UI with vanilla JS frontend.
- `project/` — archived reference docs, scripts, and legacy setup guides carried over from the original repo.

## Deployment and release workflow

- **Source of truth for development:** `https://github.com/henryy-collab/invoice-manager-core`.
- **Deployment mirror:** `https://github.com/FirstPage-Glass/invoice-manager-core`.
- Coolify is configured to deploy from the deployment mirror's `master` branch with auto-deploy enabled.
- To release a new version, sync the source-of-truth `master` to the deployment mirror:
  ```powershell
  git checkout master
  git pull origin master
  git push glass master
  ```
- The deployment mirror should only receive updates when a release is intended.
- Full instructions are in `docs/DEPLOYMENT.md`.

## Before doing any work
1. Ensure the working directory is the repo root:
   ```powershell
   cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
   ```
2. Run git pull to get the latest changes.
3. Make sure the package is installed:
   ```powershell
   python -m pip install -e .
   ```

## How to run tests
```powershell
cd local
python -m pytest
cd ..\ui
python -m pytest
```

## How to run the UI
```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
python ui\web_ui.py
```
Then open http://127.0.0.1:8000.

## Architecture notes
- The parser is intentionally modular: extractor, classifier, parsers, filename, files, processor, config.
- The UI mirrors this: services, routers, models.
- Config is driven by a `document_types` registry; each type has its own classifier, field parsers, filename template, placeholders, manual-review fields, and report column mappings. Global settings (folders, features, filename prefix/patterns, rclone, reports, google_sheets) remain at the top level.
- Frontend JS is split into:
  - `ui/static/js/core/` — shared utilities and router (`api.js`, `utils.js`, `app.js`).
  - `ui/static/js/features/local/` — parser-specific UI (`files.js`, `workflow.js`, `config.js`, `logs.js`).
  - `ui/static/js/features/shared/` — reusable components (`modal.js`).
- Future features should be added as new modules under `ui/invoice_ui/` and `ui/static/js/features/`.

## Configuration
- Copy `local/local_config.example.json` to `local/local_config.json`.
- `local/local_config.json` is machine-specific and excluded from Git.
- Relative paths in config are resolved from the **project root** (the directory containing `.git`). For example, `local/data` resolves to `<repo-root>/local/data`, and `keys/service-account.json` resolves to `<repo-root>/keys/service-account.json`.
- Runtime data lives in `local/data/` (incoming, outgoing, archive, logs, reports, state). It is created automatically on startup and excluded from Git.
- The active document type is determined by classifier patterns on the extracted text; `default_document_type` is used when no type matches.

## User's working style
When implementing anything new, follow this approach:
1. Plan first
   - Read the relevant README and code before writing anything.
   - Propose the plan and ask for confirmation before executing.
   - Break the work into small, explicit steps.
2. Break code down
   - One file per responsibility.
   - Keep functions short and focused.
   - Mirror the existing modular structure of the parser and UI.
   - Avoid giant files that mix unrelated logic.
3. Step by step
   - Implement one piece at a time.
   - Verify each piece before moving to the next.
   - Do not batch unrelated changes.
4. Test as you go
   - Add or update tests for new behavior.
   - Run existing tests after every meaningful change.
   - Both parser and UI have test suites — run both.
5. Update documentation
   - Update `docs/CHANGELOG.md`, `README.md`, `local/README.md`, and `docs/SERVICE_ACCOUNT_SETUP.md` when behavior, config, or workflow changes.
   - Keep `project/docs/AGENTS.md` current with architecture and config pointers.
   - Documentation changes are part of the feature, not an afterthought.
6. Good error handling and logging
   - Validate inputs early and return clear errors.
   - Use the existing logger for backend events.
   - Surface user-friendly messages in the UI.
   - Never silently swallow exceptions.
7. Match existing conventions
   - No comments unless asked.
   - Follow existing naming, formatting, and file organization.
   - Reuse existing utilities before writing new ones.
8. Do not surprise
   - No commits unless explicitly asked.
   - No large refactors without discussion.
   - Keep changes minimal and focused on the task.

## Style conventions
- No comments unless asked.
- Keep modules small and single-purpose.
- Match existing code style.
- Run tests after changes.
- Update documentation when behavior changes.
- Do not commit unless explicitly asked.

## Quick reference
- Core README: `README.md`
- Local parser README: `local/README.md`
- Core changelog: `docs/CHANGELOG.md`
- Service account setup: `docs/SERVICE_ACCOUNT_SETUP.md`
- Deployment guide: `docs/DEPLOYMENT.md`
- Document types roadmap and architecture: `project/extendingfunctionality/`
- Active development docs: `project/docs/AGENTS.md`, `project/docs/CHEATSHEET.md`, `project/docs/TECH_DEBT.md`
- Archived reference docs: `project/docs/archive/` (including `LINUX_SHARED_SETUP.md` and `MACOS_SETUP.md`)
- Archived legacy README: `project/README-legacy.md`
- Archived scripts: `project/scripts/`
- Archived systemd unit: `project/systemd/`

## Legacy references warning
This repo was split from the original `invoice-manager` repo, and files under `project/` are archived as-is for reference. They may still contain outdated pointers such as:
- The old repo path (`C:\Users\Henry Yau\Apps\invoice-manager`).
- The old external data folder (`invoice-manager-data/`).
- Linux/macOS setup instructions that assume a different directory layout.
- References to files or folders that no longer exist in core (`v2/`, `scripts/` at root, `systemd/` at root, etc.).

When `project/` contents change, update the reference lists in this file ("Quick reference" and "Legacy references warning") so the archive index stays accurate.

Do not follow any path, command, or instruction from `project/` without first verifying it against the current core repo layout. If something looks legacy or contradictory, flag it and ask for clarification before acting on it.

## Recent changes and current state

See `docs/CHANGELOG.md` for a full history of merged features.

### Deployment workflow

- Development happens in `henryy-collab/invoice-manager-core`.
- The deployment mirror is `FirstPage-Glass/invoice-manager-core`.
- Coolify auto-deploys from the deployment mirror `master` branch.
- To release: sync `master` from the source of truth to the deployment mirror with `git push glass master`.
- See `docs/DEPLOYMENT.md` for the full procedure.

### Current runtime flow

1. rclone pulls raw PDFs to `local/data/incoming/` via `mydrive-service`.
2. In the **Process** tab, click **Process Invoices** to run the full workflow: Pull → Preview → Rename → Write info to Report → Push → Clear.
3. The flow pauses if files need manual review or a required config step is missing. Edit the table, fix the config, then click **Resume Processing**.
4. Parser classifies each PDF to a document type, parses fields using that type's config, and renames files. `.meta.json` sidecars are written to `local/data/outgoing/`.
5. Write info to Report writes processed invoice details to the configured Google Sheets spreadsheet, using each document type's `report_columns` mapping to populate the fixed columns. Output is written to an `[Auto]` tab named for the invoice month/year with an `[Auto]` suffix (e.g. `Apr 2026 [Auto]`). Existing rows are matched by **PDF Invoice No.** and updated in place with the latest values; new invoice numbers are appended. The first row of the tab shows a bold red caps warning: "COPY THIS SHEET FIRST, THEN DELETE [AUTO]. DO NOT EDIT DIRECTLY — IT BREAKS AUTOMATION." Header row is row 2 and invoice data starts at row 3. The tab is protected with a warning-only range so users can copy it and then delete the `[Auto]` tab; editing directly will show a warning. To add your own columns or formatting, duplicate the [Auto] tab in Google Sheets. Use the **Overwrite** checkbox in the Advanced panel to clear and rewrite an `[Auto]` tab instead of upserting.
6. Push uploads renamed files to `003 Finance Operations/001 Invoices/001 Google Ads/<YYYYMM>/`.
7. Clear Drive Input removes processed originals from the Shared drive input folder.
8. Click **Start Over** to reset the workflow when done. Use the **Advanced** panel for individual step actions.

### Active config pointers

- `local/local_config.json` is machine-specific and excluded from Git.
- Relative paths in config are resolved from the **project root** (the directory containing `.git`).
- Data folders should be written as `local/data`, `local/data/incoming`, etc.
- Service-account keys should be written as `keys/<file>.json` (they live next to the `local/` folder at project root).
- Current Drive paths: `003 Finance Operations/001 Invoices/001 Google Ads/000 Input Folder` and `003 Finance Operations/001 Invoices/001 Google Ads`.
- Current rclone remote: `mydrive-service`.
- Source of truth repo: `henryy-collab/invoice-manager-core`.
- Deployment mirror repo: `FirstPage-Glass/invoice-manager-core`.
- Coolify auto-deploys from the deployment mirror's `master` branch.
- Google Sheets reporting is configured under `google_sheets` in `local_config.json`. Enable it and set `spreadsheet_url` to append processed invoice details to monthly tabs based on invoice date. The Google Sheets API must be enabled in the same Cloud project.
- Document types are configured under `document_types`; the default type is `googleadsinvoice`.
- The parser captures the account **name** (`account`) and the numeric account **ID** (`account_id`) as separate fields. `account_id` is stored **digits-only** (dashes stripped, e.g. `802-155-0535` → `8021550535`) so it is a single canonical unique identifier. It is parsed from the bracketed form (`Account: Name [12345]`) or a standalone `Account ID: 12345` line, flows into parse results and `.meta.json` sidecars, and is available as the `{account_id}` filename placeholder. It is not yet mapped into CSV/Google Sheets report columns.
- A per-account breakdown (`accounts`) is parsed and written to the `.meta.json` sidecar as a JSON array of `{account, account_id, amount}` records. Multi-account invoices (consolidated HKCT) are parsed from the "Summary of costs by account budget" table and aggregated by account ID; single-account invoices produce one record with the invoice total. It is not used in filenames or reports. Configured under `parsers.accounts` / `document_types.*.fields.accounts`.
- **`GET /api/accounts`** is a separate endpoint (independent of the parse/preview/report flow) that returns an aggregated, account-keyed data array. It is **scoped to the latest run by default**: it reads `state/last_run_processed.json` (the `processed` list) and parses only that run's archived PDFs; `?scope=all` opts back into scanning the whole archive, and `?folder=` overrides the source directory (default `config.archive_folder`). It lives in `ui/invoice_ui/services/accounts_service.py` and `ui/invoice_ui/routers/accounts_router.py`.

### Known quirks

- Static assets (`styles.css`, `api.js`, etc.) are cached by browsers. After UI updates, users may need to hard-refresh (`Ctrl+F5`) for changes to appear.
- The `?` tooltip help markers rely on the updated CSS; a cached stylesheet will make them appear as plain text.

### Notes for future work

- When adding new config fields, expose them in `ui/static/js/features/local/config.js` and update the corresponding section/label/help text.
- When adding document-type-specific config, add it to `DocumentTypeConfig` in `local/invoice_parser/config.py`, the config editor in `ui/static/js/features/local/config.js`, and the migration validator if it should be auto-populated for legacy configs.
- Keep config section names and labels consistent with invoice-processing language, not backend implementation details.
- When adding new Process workflow actions, follow the existing pattern: backend method in `ui/invoice_ui/services/`, endpoint in `ui/invoice_ui/routers/`, API wrapper in `ui/static/js/core/api.js`, and UI handler in `ui/static/js/features/local/workflow.js`.
- Google Sheets report writes follow the same workflow pattern and live in `ui/invoice_ui/services/sheets_service.py` and `ui/invoice_ui/routers/sheets_router.py`.
- When changing the frontend, bump the cache-busting query string on the affected assets in `ui/static/index.html` (e.g. `?v=4`) so returning browsers load the new code.
- **Update documentation**: when adding a new feature, update `docs/CHANGELOG.md`, `docs/DEPLOYMENT.md`, `docs/SERVICE_ACCOUNT_SETUP.md`, `local/README.md`, and `README.md` as applicable. Only update archived docs under `project/` if they are still relevant to the current core app, and keep `project/docs/AGENTS.md` up to date when the archive changes.
- **Keep this AGENTS.md file current** whenever docs, config behavior, workflow steps, or architecture change. SAFEWORD
