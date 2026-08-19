# Changelog

A record of merged features and notable changes for Invoice Manager Core.

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
