# Agent Session Starter

## Active project
- Repo: `C:\Users\Henry Yau\Apps\invoice-manager-core`
- GitHub: https://github.com/henryy-collab/invoice-manager-core
- Default branch: `master`
- Note: the original `invoice-manager` repo is deprecated. Continue all work here.

## What this project is
A self-contained system for processing Google invoice PDFs:
- `local/` — Python PDF parser and renamer (CLI).
- `ui/` — FastAPI web UI with vanilla JS frontend.
- `project/` — archived reference docs, scripts, and legacy setup guides carried over from the original repo.

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
- The parser is intentionally modular: extractor, parsers, filename, files, processor, config.
- The UI mirrors this: services, routers, models.
- Frontend JS is split into:
  - `ui/static/js/core/` — shared utilities and router (`api.js`, `utils.js`, `app.js`).
  - `ui/static/js/features/local/` — parser-specific UI (`files.js`, `workflow.js`, `config.js`, `logs.js`).
  - `ui/static/js/features/shared/` — reusable components (`modal.js`).
- Future features should be added as new modules under `ui/invoice_ui/` and `ui/static/js/features/`.

## Configuration
- Copy `local/local_config.example.json` to `local/local_config.json`.
- `local/local_config.json` is machine-specific and excluded from Git.
- Runtime data lives in `local/data/` (incoming, outgoing, archive, logs, reports, state). It is created automatically on startup and excluded from Git.

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
5. Good error handling and logging
   - Validate inputs early and return clear errors.
   - Use the existing logger for backend events.
   - Surface user-friendly messages in the UI.
   - Never silently swallow exceptions.
6. Match existing conventions
   - No comments unless asked.
   - Follow existing naming, formatting, and file organization.
   - Reuse existing utilities before writing new ones.
7. Do not surprise
   - No commits unless explicitly asked.
   - No large refactors without discussion.
   - Keep changes minimal and focused on the task.

## Style conventions
- No comments unless asked.
- Keep modules small and single-purpose.
- Match existing code style.
- Run tests after changes.
- Do not commit unless explicitly asked.

## Quick reference
- Core README: `README.md`
- Local parser README: `local/README.md`
- Core changelog: `docs/CHANGELOG.md`
- Service account setup: `docs/SERVICE_ACCOUNT_SETUP.md`
- Archived reference docs: `project/docs/`
- Archived legacy README: `project/README-legacy.md`

## Legacy references warning
This repo was split from the original `invoice-manager` repo, and some files under `project/` are archived as-is for reference. They may still contain outdated pointers such as:
- The old repo path (`C:\Users\Henry Yau\Apps\invoice-manager`).
- The old external data folder (`invoice-manager-data/`).
- Linux/macOS setup instructions that assume a different directory layout.
- References to files or folders that no longer exist in core (`v2/`, `scripts/` at root, `systemd/` at root, etc.).

Do not follow any path, command, or instruction from `project/` without first verifying it against the current core repo layout. If something looks legacy or contradictory, flag it and ask for clarification before acting on it.

## Recent changes and current state

See `docs/CHANGELOG.md` for a full history of merged features.

### Current runtime flow

1. rclone pulls raw PDFs to `local/data/incoming/` via `mydrive-service`.
2. In the **Process** tab, click **Process Invoices** to run the full workflow: Pull → Preview → Rename → Write info to Report → Push → Clear.
3. The flow pauses if files need manual review or a required config step is missing. Edit the table, fix the config, then click **Resume Processing**.
4. Parser renames files and writes `.meta.json` sidecars to `local/data/outgoing/`.
5. Write info to Report appends processed invoice details (Client Ref., PDF Invoice Date, PDF Invoice No., Topped Currency, Topped amount) to the configured Google Sheets spreadsheet, in an `[Auto]` tab named for the invoice month/year with an `[Auto]` suffix (e.g. `Apr 2026 [Auto]`). The first row of the tab shows a bold red caps warning: "COPY THIS SHEET FIRST, THEN DELETE [AUTO]. DO NOT EDIT DIRECTLY — IT BREAKS AUTOMATION." Header row is row 2 and invoice data starts at row 3. The tab is protected with a warning-only range so users can copy it and then delete the `[Auto]` tab; editing directly will show a warning. To add your own columns or formatting, duplicate the [Auto] tab in Google Sheets.
6. Push uploads renamed files to `003 Finance Operations/001 Invoices/001 Google Ads/<YYYYMM>/`.
7. Clear Drive Input removes processed originals from the Shared drive input folder.
8. Click **Start Over** to reset the workflow when done. Use the **Advanced** panel for individual step actions.

### Active config pointers

- `local/local_config.json` is machine-specific and excluded from Git.
- Current Drive paths: `003 Finance Operations/001 Invoices/001 Google Ads/000 Input Folder` and `003 Finance Operations/001 Invoices/001 Google Ads`.
- Current rclone remote: `mydrive-service`.
- Google Sheets reporting is configured under `google_sheets` in `local_config.json`. Enable it and set `spreadsheet_url` to append processed invoice details to monthly tabs based on invoice date. The Google Sheets API must be enabled in the same Cloud project.

### Known quirks

- Static assets (`styles.css`, `api.js`, etc.) are cached by browsers. After UI updates, users may need to hard-refresh (`Ctrl+F5`) for changes to appear.
- The `?` tooltip help markers rely on the updated CSS; a cached stylesheet will make them appear as plain text.

### Notes for future work

- When adding new config fields, expose them in `ui/static/js/features/local/config.js` and update the corresponding section/label/help text.
- Keep config section names and labels consistent with invoice-processing language, not backend implementation details.
- When adding new Process workflow actions, follow the existing pattern: backend method in `ui/invoice_ui/services/`, endpoint in `ui/invoice_ui/routers/`, API wrapper in `ui/static/js/core/api.js`, and UI handler in `ui/static/js/features/local/workflow.js`.
- Google Sheets report writes follow the same workflow pattern and live in `ui/invoice_ui/services/sheets_service.py` and `ui/invoice_ui/routers/sheets_router.py`.
- When changing the frontend, bump the cache-busting query string on the affected assets in `ui/static/index.html` (e.g. `?v=4`) so returning browsers load the new code.
- **Update documentation**: when adding a new feature, update `docs/CHANGELOG.md`, `docs/SERVICE_ACCOUNT_SETUP.md`, `local/README.md`, and `README.md` as applicable. Only update archived docs under `project/docs/` if they are still relevant to the current core app.
