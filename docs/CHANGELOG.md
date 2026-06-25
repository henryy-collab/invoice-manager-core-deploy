# Changelog

A record of merged features and notable changes for Invoice Manager Core.

## 2026-06-25 — Currency column in Google Sheets report

- Google Sheets report rows now include **Topped Currency** before **Topped amount**.
- The protected `[Auto]` tab header row is updated automatically on the next write.
- CSV report already includes Topped Currency; no change required.

## 2026-06-25 — Warning-only protection for [Auto] sheets

- `[Auto]` sheets are now protected with `warningOnly: True`, so users can copy and delete them after seeing a warning.
- The first row of each `[Auto]` sheet contains a bold red caps warning: "COPY THIS SHEET FIRST, THEN DELETE [AUTO]. DO NOT EDIT DIRECTLY — IT BREAKS AUTOMATION."
- Header row moved to row 2; invoice data starts at row 3.
- The protection warning dialog still appears when users try to edit cells.

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
