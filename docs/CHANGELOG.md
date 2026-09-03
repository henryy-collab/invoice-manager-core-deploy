# Changelog

A record of merged features and notable changes for Invoice Manager Core.

## 2026-09-02 — chore: untrack machine-specific local_config.json

- `local/local_config.json` is now gitignored instead of tracked. It contains machine-specific paths and has never been meaningfully committed (committed copy was stale); keeping it tracked invites accidental resets that destroy the working config (e.g. `git reset --hard`).
- Copy `local/local_config.example.json` to `local/local_config.json` on each machine to create it. Deployments are unaffected — they configure via the `APP_CONFIG_JSON` env var.
- Updated `AGENTS.md` / `README.md` to reflect that the file is never committed.

## 2026-09-02 — fix: rclone push/clear reject filenames starting with `#`

- `SyncService.push_outgoing` and `SyncService.clear_remote_input` now write the per-run file list with `--files-from-raw` instead of `--files-from`.
- Root cause: rclone's `--files-from` treats lines starting with `#` or `;` as comments, so a renamed invoice whose account name starts with `#` (e.g. `#24123_-_st.com_-_Facebook_...`) was silently skipped by the push copy — it then ran the successful-path cleanup, deleting the local outgoing copy without uploading it. `--files-from-raw` reads every line verbatim.
- `clear_remote_input` also kept its list file alive for the whole platform loop — previously the list file was unlinked after the first platform's rclone call, so the second platform's delete ran against a deleted file. The cleanup now happens once after the loop.
- **Tests**: new `ui/tests/test_sync_service.py` cases asserting a `#`-prefixed target name is passed through for both push and clear.

## 2026-09-02 — account_id report column; Platform carries document type

- **New `Account ID` report column** (index 1, after `Client Ref.`) in both the Google Sheets report rows and the CSV export (`sheets.py` `HEADER_COLUMNS`, `reports_service.py` `_COLUMNS`/`ReportRow`).
- Wired `account_id` parsing for **Google** invoices: added the `account_id` field (`parser: account_id`) to `google_ads` in `local_config.json` (facebook already had it), so google sidecars/rows now carry digits-only account IDs (dashes stripped, e.g. `933-864-1234` → `9338641234`).
- **`document_type` now shows in the `Platform` column only** for both types; removed the `document_type → Invoice Type` mapping (`Invoice Type` column header remains but is empty until mapped).
- Config `report_columns` for both types now map `account_id → "Account ID"` and `platform → "Platform"`.
- `config.py` flat→registry migration default report columns updated to match; UI config editor (`config.js`) fixed-columns list now includes `Account ID` (cache-buster `?v=11`).
- **Tests**: report column index assertions updated, new `test_format_row_reports_account_id`, google `account_id` dash-strip extraction test, CSV `Account ID` assertion in UI tests.

## 2026-09-02 — Per-platform wiring by document type (Google + Meta)

- The app now routes files and reports **by classified document type**. Google (`google_ads`) and Meta (`facebook`) invoices are pulled from their own Drive input folders, pushed to their own Drive destination folders, and reported to their own Google Sheets workbooks — all from a single shared workflow.
- **New `platforms` config section** in `local_config.json` / `local_config.example.json`: optional per-type `rclone` and `google_sheets` overlays that merge on top of the top-level defaults (top-level `rclone`/`google_sheets` remain the `google_ads`/default configuration). New `AppConfig.platforms`, `PlatformConfig`, and helpers `rclone_for()`, `google_sheets_for()`, `platform_types()` in `local/invoice_parser/config.py`.
- **Pull** (`SyncService.pull_incoming`): copies each platform's `source_drive_folder` into the shared `incoming/` using `rclone copy` (not `sync`, which would delete the other platform's files).
- **Push** (`SyncService.push_outgoing`): reads each renamed PDF's `.meta.json` `document_type`, resolves that platform's `destination_drive_folder`, and groups into its `{year}{month}` subfolder.
- **Clear remote input** (`SyncService.clear_remote_input`): deletes the processed list from each platform's `source_drive_folder`.
- **Reports** (`SheetsService.write_preview_results`): preview documents are grouped by `document_type` and written to that platform's spreadsheet via `google_sheets_for()` (`facebook` → `1ckywITADXmCUlSVI75XPii9SU6rbenNHDwJ3tl6qMS4`, `google_ads` → existing `1Rngh…RKgas`). The `Platform`/`Invoice Type` columns continue to label rows.
- **Sync status** now reports the resolved per-platform configuration list.
- **Tests**: new `local/tests/test_platforms.py` (merge/fallback helpers) and per-platform pull/push/clear coverage in `ui/tests/test_sync_service.py`.

## 2026-09-02 — Report document type in the `Platform` column (both platforms)

- The report **Platform column** now reports the classified document type (`google_ads` / `facebook`) for every row, in both the Google Sheets report and the CSV export.
- Implemented as a `platform` pseudo-field alongside `document_type` in the reporting row builders (`local/invoice_parser/reports/sheets.py` `_format_row` and `ui/invoice_ui/services/reports_service.py` `_result_to_row`): mapping `"platform": "Platform"` in a type's `report_columns` populates it with the document type.
- Added `"platform": "Platform"` to the `report_columns` of both `google_ads` and `facebook`.
- Added the missing `document_type → Invoice Type` mapping to the live `google_ads` config so its Google Sheets rows report the invoice type like `facebook` already did.

## 2026-09-02 — Document type key rename (`googleadsinvoice` → `google_ads`, `meta_ads` → `facebook`)

- Renamed the `document_types` registry keys to match platform-facing names: `googleadsinvoice` → `google_ads`, `meta_ads` → `facebook`.
- Updated `default_document_type` to `google_ads`, the parser default (`models.py`), the UI schema default (`schemas.py`), both config files, and all tests/docs references.
- Behavior and parsing configuration are unchanged — only the type identifiers in `.meta.json` sidecars and the **Invoice Type** column change (e.g. `google_ads`, `facebook`).
- Added a new `facebook` document type for Meta (Facebook/Meta Platforms) invoices: parses `PO Number`, `Account Id / Group`, `Invoice #`, `Invoice Date` (`%d-%b-%Y`), `Invoice Currency`, and `Invoice Total`.

## 2026-09-02 — Report the identified invoice type

- The parsed `document_type` (e.g. `googleadsinvoice`) is now reported wherever invoice data goes out.
- **`.meta.json` sidecars** now include a `document_type` field (`write_metadata_file`), so archived/outgoing metadata records the classified type.
- **Google Sheets report**: new **Invoice Type** column appended to the fixed `HEADER_COLUMNS`. Map `document_type` in a type's `report_columns` to populate it.
- **CSV export**: new **Invoice Type** column in the exported report; populated from the preview result's `document_type`.
- **NocoDB upload**: `document_type` added to the default `column_map` (`document_type → invoice_type`).
- **Config editor**: the report-columns mapping in the UI now offers the **Invoice Type** column and a `document_type` field option.
- **Tests**: sidecar, Sheets `_format_row`, NocoDB payload, and CSV-export coverage added; both suites pass.

## 2026-09-02 — Subagent task-breaking guidance

- Added a **"Working with subagents"** section to the root `AGENTS.md` and an item in the `project/docs/AGENTS.md` "User's working style": break large tasks into small, single-responsibility parts, give each part its own verification, pack subagent prompts with full context, and re-run both test suites after integrating subagent output.

## 2026-08-25 — NocoDB upload CLI

- **New `upload_nocodb.py`**: uploads parsed invoice `.meta.json` sidecars from `output_folder` to a NocoDB `Invoices` table via the v3 REST API (`xc-token` auth).
- **New `invoice_parser/nocodb.py`**: `upload_invoices()` maps each sidecar's parsed fields to NocoDB columns and `POST /api/v3/data/{base}/{table}/records`; `upload_from_config()` drives it from the `nocodb` config section. `source` (a NocoDB dropdown) is uploaded empty because the app does not parse a source value yet.
- **New `nocodb` config section** in `AppConfig` / `local_config.example.json`: `{enabled, base_id, table_id, column_map}`. Default column mapping: `account→ad_account_name`, `account_id→account_id`, `number→pdf_invoice_number`, `date→pdf_invoice_date`, `total→topped_amount`, `currency→currency`, `source→source`.
- **Env vars**: `NOCODB_TOKEN` (renamed from `NOCO_TOKEN`) and `NOCODB_URL` (default `http://localhost:3000`), both gitignored in `.env`.
- **Tests**: `local/tests/test_nocodb.py` covers payload mapping (incl. empty `source`), dry-run, missing-token, and config-disabled/id-less paths.

## 2026-08-19 — Account-keyed data endpoint and normalized account IDs

- **`GET /api/accounts`** (new, separate from the parse/report flow): returns a JSON array of extracted fields keyed by `account_id` as the unique identifier.
  - **Scoped to the latest run by default**: reads `state/last_run_processed.json` (the `processed` list) and parses only that run's archived PDFs, so it reflects the most recent monthly run instead of repeating prior months. `processed` files only; manual-review files are excluded.
  - `GET /api/accounts?scope=all` opts back into scanning the whole archive folder.
  - Reads the archived processed PDFs (`local/data/archive/`, where every run accumulates) by default; an optional `?folder=` query parameter can point elsewhere.
  - Records are aggregated by `account_id`: `{account_id, account, amount, invoice_count, invoices:[{number, date, currency, amount}]}`.
  - `date` is normalized to ISO (`2026-06-30`); amounts are summed per account and formatted as 2-decimal strings.
  - New `accounts_service.py` + `accounts_router.py`, registered in the app.
- **Account IDs are now digits-only**: the parser strips dashes from `account_id` (`802-155-0535` → `8021550535`) everywhere it is extracted — the `account_id` field, the `accounts` breakdown, sidecars, and the new endpoint — so it is a single canonical unique identifier.

## 2026-08-19 — Per-account breakdown in `.meta.json` sidecar

- **New `accounts` field**: each parsed invoice now includes a per-account breakdown linking each account name to its own account ID and amount.
- **Multi-account invoices** (e.g. consolidated HKCT invoices with several accounts) are parsed from the "Summary of costs by account budget" table. Account budget rows are aggregated by account ID, so each account appears once with its total (negative amounts, e.g. credit notes, are preserved).
- **Single-account invoices** produce one record using the account name, account ID, and the invoice total.
- The `accounts` value is stored as a JSON list inside the `.meta.json` sidecar (e.g. `[{"account":"HKCT - Brand","account_id":"802-155-0535","amount":"804.21"}, ...]`).
- New `parsers.accounts` (and per-document-type `fields.accounts`) config, exposed in the UI Config tab. It is not mapped into the CSV or Google Sheets report.
- Validated against all 131 archived real invoices: every invoice yields at least one record, and the sum of account amounts matches the invoice total on every file.

## 2026-08-19 — Separate account ID field

- **New `account_id` field**: the PDF parser now captures the account ID separately from the account name.
  - `account` is the account name only (e.g. `Test Client` from `Account: Test Client [12345]`).
  - `account_id` captures the numeric ID from either the bracketed form (`[12345]`) or a standalone `Account ID: 12345` line.
  - Invoices that only contain an account ID (no account name) now go to manual review instead of using the ID as the name.
- The account ID flows through parse results, `.meta.json` sidecars, the filename placeholder `{account_id}`, and the UI preview table (new editable Account ID column). It is not yet mapped into the CSV or Google Sheets reports.
- New `account_id` config: `parsers.account_id` (and per-document-type `fields.account_id`), plus `account_id` filename placeholder defaults.
- UI Config tab now exposes Account ID parser and placeholder options; frontend assets cache-busted to `?v=8`.

## 2026-08-05 — Documented release workflow

- Source of truth for development: `henryy-collab/invoice-manager-core`.
- Deployment mirror: `FirstPage-Glass/invoice-manager-core`.
- Coolify watches the deployment mirror's `master` branch and auto-deploys when it is synced.
- Release command: `git push glass master` from the source-of-truth `master`.
- Updated `docs/DEPLOYMENT.md`, `README.md`, and `project/docs/AGENTS.md` with the workflow.

## 2026-08-04 — Defensive deployment and runtime fixes

- **`deploy/entrypoint.sh`**: now supports plain env vars (`SERVICE_ACCOUNT_JSON`, `APP_CONFIG_JSON`, `RCLONE_CONF`) in addition to base64 env vars and file mounts, so existing Coolify env vars work without changes.
- **`deploy/repair_config.py`**: added startup config repair that restores parser patterns from `local/local_config.example.json` while preserving environment-specific settings (Drive paths, spreadsheet URL, timezone, etc.).
- **`local/invoice_parser/logging.py`**: creates the log directory before opening the log file, preventing startup crashes when the directory is missing.
- **`ui/web_ui.py`**: creates all configured directories on startup (`input_folder`, `output_folder`, `archive_folder`, and the log directory).
- **`ui/invoice_ui/services/sync_service.py`**: an empty or missing `archive_drive_folder` is now treated as disabled, preventing accidental archives to the Google Drive root.
- **Better rclone diagnostics**: `sync_service.py` now summarizes common rclone failures (missing folder, permission denied, auth failure, timeout) into a single readable message.
- **Tests**: added `local/tests/test_logging.py`, `ui/tests/test_web_ui.py`, and `ui/tests/test_sync_service.py` to cover the new defensive behavior.
- **Docker layout**: root `docker-compose.yml` is now the Coolify env-var compose; local file-mount development uses `deploy/docker-compose.local.yml`.

## 2026-07-03 — Document types architecture and config-driven parsing

- **Document types registry**: `local/local_config.json` now has a top-level `document_types` section. Each type owns its own classifier, field parsers, filename template, placeholders, manual-review fields, and report column mappings.
- **Document type classification**: PDFs are classified by matching keyword patterns in the extracted text; the best-matching document type's config is used for parsing and filename generation.
- **Strategy-based field parsing**: field parsers are selected by the `parser` key inside each document type's `fields` config, making it easier to add new document types and custom parsers.
- **Per-document-type reports**: CSV and Google Sheets output now use each document type's `report_columns` mapping to populate the fixed column headers.
- **Document types config editor**: the UI Config tab now shows a document-type selector and per-type editor for classifier, filename, placeholders, field parsers, manual-review fields, and report columns.
- **Config migration**: when `document_types` is missing, the app automatically builds a default `googleadsinvoice` type from the old flat `parsers`, `filename_template`, and `features.manual_review_for_missing` settings.

## 2026-07-03 — Upsert Google Sheets report by PDF Invoice No.

- `Write info to Report` now uses the **PDF Invoice No.** column as the unique key.
- Existing invoice numbers are updated in place with the latest parsed values instead of being skipped or duplicated.
- New invoice numbers are appended to the bottom of the sheet.
- Existing `[Auto]` sheets are no longer cleared or reformatted when re-opened; the warning and header rows are only written for new sheets.
- Warning row is now merged across all header columns, larger, bold, red text on a bright yellow background, and center-aligned.
- The **Overwrite** checkbox remains available in the Advanced panel as a legacy option to clear and rewrite the sheet.


- The total parser now looks for `Total amount due in <CURRENCY>` / `Total in <CURRENCY>` and returns the **last amount** in the following block.
- This fixes wrong totals caused by PDF column layout reordering lines during text extraction.
- Negative credit-note totals (e.g., `-HK$40.83`) are now preserved.

## 2026-07-03 — Root-relative config paths

- All relative paths in `local/local_config.json` are now resolved from the project root (the directory containing `.git`).
- This lets the service-account key live in a top-level `keys/` folder while data folders stay under `local/data/`.
- Paths are persisted back as relative values when saved through the UI.

## 2026-06-25 — Currency column in Google Sheets report

- Google Sheets report rows now include **Topped Currency** before **Topped amount**.
- The protected `[Auto]` tab header row is updated automatically on the next write.
- CSV report already includes Topped Currency; no change required.

## 2026-06-25 — Warning-only protection for [Auto] sheets

- `[Auto]` sheets are now protected with `warningOnly: True`, so users can copy and delete them after seeing a warning.
- The first row of each `[Auto]` sheet contains a bold red caps warning: "COPY THIS SHEET FIRST, THEN DELETE [AUTO]. DO NOT EDIT DIRECTLY — IT BREAKS AUTOMATION."
- Header row moved to row 2; invoice data starts at row 3.
- The protection warning dialog still appears when users try to edit cells.

## 2026-06-25 — Start Over can clear outgoing folder

- The Start Over modal now offers a second checkbox: "Clear local outgoing folder before starting over".
- When checked, all files in `local/data/outgoing/` (renamed PDFs and `.meta.json` sidecars) are deleted before the workflow resets.
- The existing "Clear local incoming folder" checkbox behavior is unchanged.

## 2026-06-24 — Protected [Auto] Google Sheets tabs

- Google Sheets report tabs now use an `[Auto]` suffix (e.g. `Apr 2026 [Auto]`).
- New [Auto] tabs are protected so only the service account can edit them.
- Users can duplicate an [Auto] tab to make their own editable copy; the app only writes to the protected [Auto] tab.

## 2026-06-24 — Split into invoice-manager-core

- Created `invoice-manager-core` as a self-contained repo for the working parser and web UI.
- Runtime data now lives in `local/data/` (incoming, outgoing, archive, logs, reports, state) and is created automatically on startup.
- Removed from this repo: Google Apps Script downloader (`v2/`), Linux shell scripts, systemd unit, and platform-specific macOS/Linux setup guides.
- Kept: parser package, web UI, tests, and service-account setup documentation for optional Google Drive sync.

## 2026-06-24 — Process tab consolidation

- **Single-button workflow**: the Process tab now uses one primary **Process Invoices** button in the Workflow panel header. It runs Pull → Preview → Rename → Write info to Report → Push → Clear automatically.
- **Pause and resume**: the flow stops if rclone is not configured, files need manual review, or a step fails. The primary button becomes **Resume Processing** so you can fix the issue and continue from where it stopped.
- **Start Over**: resets the workflow. An optional checkbox clears the local incoming folder.
- **Advanced panel**: individual step actions (Pull, Preview, Rename, Write info to Report, Push, Push Archive, Clear Drive Input) are now in a collapsible Advanced panel below the preview table.
- **Timeline status icons**: each workflow step shows waiting/running/done/paused state, and a progress bar appears below the status bar.
- **Report guard**: Write info to Report is only available after a successful Rename.
- **Sheets error handling**: Google Sheets auth/config errors now return structured UI messages instead of HTTP 500.
- **Service account path**: relative `google_sheets.service_account_file` paths are resolved against the project root.

## 2026-06-24 — Google Sheets report

- **Google Sheets report**: appends processed invoice details (Client Ref., PDF Invoice Date, PDF Invoice No., Topped amount) to a configured Google Sheets spreadsheet. Rows are grouped into monthly tabs based on the invoice date (e.g. `Apr 2026`, `May 2026`). A tab and header row are created automatically if missing. Duplicates are skipped by invoice number. Requires the Google Sheets API to be enabled and the service account to have editor access to the spreadsheet.
- New UI workflow step: **Write info to Report**, also included in **Process End-to-End**.
- New `google_sheets` config section in `local/local_config.json`.
- Reuses the existing service-account key configured for rclone.

## 2026-06-24 — Service account authentication

- The recommended way to access Google Drive from the shared PC is now a service-account JSON key with rclone. See `docs/SERVICE_ACCOUNT_SETUP.md`.

## Earlier merged work

- **Local data folders**: `local/local_config.json` now uses local folders under `invoice-manager-data/` instead of a Google Drive for Desktop mount.
- **Date-organised Drive output**: processed files are pushed to subfolders based on invoice date using `rclone.destination_subfolder_template` (e.g. `{year}{month}`).
- **Batch rclone push**: outgoing files are grouped by target subfolder and pushed with a single rclone invocation per subfolder.
- **Clear Drive Input Folder**: deletes only the files that were successfully processed in the last run from the Drive input folder.
- **Complete config tab**: the UI exposes `archive.mode`, `date.details_block.*`, and `filename.placeholders.*`.
- **User-friendly config labels**: config section names and field labels were rewritten for non-technical users, with `?` hover tooltips explaining each option.
- **Files tab reorganisation**: the Files tab now shows two collapsible tables, one for incoming and one for outgoing files.
- **Unified Process tab**: the former Preview/Run and Sync tabs have been merged into a single Process tab with a numbered workflow panel (Pull, Preview, Review/Edit, Rename, Push, Clear). Actions were renamed: Run → Rename Files, Run Full Flow → Process End-to-End.
- **Inline field editing**: missing or incorrect invoice fields can be edited directly in the Process preview table.
- **Dashboard tab removed**: the navigation bar now shows Process, Files, Config, Logs. Folder and config information moved to the Files tab.
- **Removed**: `features.cleanup_after_processing` is no longer needed because files move from incoming to outgoing and Drive input cleanup is handled separately.
