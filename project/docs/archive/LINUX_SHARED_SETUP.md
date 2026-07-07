# Linux Shared Setup

Guide for running Invoice Manager Core on a shared Linux PC with a Google Shared drive and rclone.

This file is archived under `project/docs/archive/`. It is a legacy reference for a Linux/server deployment and may need path adjustments for your environment.

---

## Overview

```
Google Shared Drive
├── <Shared drive input folder>/        ← GAS downloader saves raw PDFs here
└── <Destination folder>/             ← processed files end up here

        ↑↓  rclone sync
/var/invoice-manager/incoming/      ← app reads raw PDFs from here
/var/invoice-manager/outgoing/      ← app writes renamed PDFs here
/var/invoice-manager/archive/       ← optional local backup of originals
```

The app never touches Google Drive directly. It only reads/writes local files. rclone handles the sync.

---

## Prerequisites

- Linux shared PC accessible via RDP/SSH.
- Google account or service account with access to the Shared drive folders.
- Python 3.11+ installed.

---

## 1. Install rclone

```bash
sudo -v
curl https://rclone.org/install.sh | sudo bash
```

### Configure rclone with a service account (recommended)

On a shared PC, use a Google service account instead of a personal Google account. This keeps the personal account off the machine and lets you scope access to a single JSON key.

Follow the full setup guide:

- [Service Account Setup](../../docs/SERVICE_ACCOUNT_SETUP.md)

The quick summary is:

1. Create a service account in Google Cloud, enable the Drive API, and download a JSON key.
2. Add the service account to the Shared drive with **Content manager** access.
3. Configure the `mydrive-service` rclone remote with `service_account_file` and the Shared drive ID.
4. Verify with:

   ```bash
   rclone lsd mydrive-service:
   ```

### Alternative: configure rclone with OAuth

If you cannot use a service account, follow the OAuth flow instead:

```bash
rclone config
```

Choose `n` for new remote, name it `mydrive-service`, type `drive`, then follow the OAuth flow. On a headless server, rclone prints a URL to open on your local machine.

---

## 2. Set up local folders

```bash
sudo mkdir -p /var/invoice-manager/{incoming,outgoing,archive,logs,reports,state}
sudo chown -R $USER:$USER /var/invoice-manager
```

---

## 3. Install the app

```bash
cd /opt/invoice-manager-core
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

---

## 4. Configure

Copy the example config:

```bash
cp local/local_config.example.json local/local_config.json
```

Edit `local/local_config.json`:

```json
{
  "source_folder": "/var/invoice-manager",
  "input_folder": "/var/invoice-manager/incoming",
  "output_folder": "/var/invoice-manager/outgoing",
  "archive_folder": "/var/invoice-manager/archive",
  "log_file": "/var/invoice-manager/logs/parse_and_rename.log",
  "timezone": "Asia/Hong_Kong",

  "features": {
    "archive": true,
    "skip_already_processed": true,
    "manual_review_for_missing": ["account", "date"],
    "number_fallback_to_filename": true,
    "deduplicate_within_run": true,
    "dry_run": false
  },

  "archive": {
    "mode": "copy_original"
  },

  "rclone": {
    "enabled": true,
    "remote": "mydrive-service",
    "source_drive_folder": "003 Finance Operations/001 Invoices/001 Google Ads/000 Input Folder",
    "destination_drive_folder": "003 Finance Operations/001 Invoices/001 Google Ads",
    "destination_subfolder_template": "{year}{month}",
    "archive_drive_folder": null
  },

  "reports": {
    "enabled": true,
    "filename_template": "parsed_fields_{timestamp}.csv"
  },

  "google_sheets": {
    "enabled": true,
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit",
    "service_account_file": "/opt/invoice-manager-core/.secrets/service-account.json",
    "tab_name_template": "%b %Y",
    "date_format": "%d/%m/%Y",
    "skip_existing_by": "number",
    "raw_sheet_suffix": " [Auto]",
    "protect_raw_sheets": true
  },

  "filename": {
    "placeholders": {
      "account": {"sanitize": true, "fallback": "UNKNOWN"},
      "number": {"sanitize": true, "fallback": "unknown"},
      "date": {"fallback": "unknown-date"},
      "total": {"fallback": "unknown"},
      "currency": {"fallback": "unknown"}
    },
    "manual_review_prefix": "000_",
    "already_processed_patterns": [
      "_Invoice_\\d{8}\\.pdf$",
      "_unparsed\\.pdf$",
      "^000_"
    ],
    "collision_suffix": "_{counter}"
  }
}
```

Set `rclone.archive_drive_folder` to a Drive folder path if you also want to sync the local archive back to Drive. Leave it `null` to keep archive local only.

Set `google_sheets.enabled` to `true` to append processed invoice details to a Google Sheets report. Rows are grouped into tabs by invoice month/year. The service account must have editor access to the spreadsheet, and the Google Sheets API must be enabled in the Cloud project.

### Folder paths

`source_drive_folder` and `destination_drive_folder` are paths within your Google Drive or Shared drive, relative to the root. Use forward slashes for nested folders:

```
SharedDriveName/Department/InvoicesRAW
My Drive/Invoices
003 Finance Operations/001 Invoices/001 Google Ads
```

If using a Shared drive, the remote must be configured with Shared drive support (`Configure this as a Shared Drive? y`).

---

## 5. Configure the Google Apps Script downloader

In the Apps Script project, set the Script Property:

- Key: `DESTINATION_FOLDER_ID`
- Value: the folder ID of the Shared drive input folder

This makes the GAS downloader save all raw invoice attachments into the input folder.

---

## 6. Sync from Google Drive

You can pull from the web UI (**Process** tab) or from the terminal.

### From the terminal

Pull raw invoices from the input folder:

```bash
/opt/invoice-manager-core/project/scripts/sync-incoming.sh
```

---

## 7. Run the web UI

### Option A: Manual start

```bash
cd /opt/invoice-manager-core
source .venv/bin/activate
python ui/web_ui.py
```

Open in a browser:

```
http://<shared-pc-ip>:8000
```

The default tab is **Process**.

### Option B: Always-on via systemd

Copy the example service file and adjust paths if needed:

```bash
sudo cp project/systemd/invoice-manager.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable invoice-manager
sudo systemctl start invoice-manager
```

Check status:

```bash
sudo systemctl status invoice-manager
```

---

## 8. Process invoices

1. In the web UI, open the **Process** tab.
2. Click **Process Invoices** in the Workflow panel header to run Pull → Preview → Rename → Write info to Report → Push → Clear automatically.
3. If the flow pauses for manual review, edit the fields in the preview table, then click **Resume Processing**.
4. Click **Start Over** to reset the workflow when you are done. You can optionally clear the local incoming and/or outgoing folders.

For individual steps, expand the **Advanced** panel below the preview table. Use **Push**, **Push Archive**, and **Clear Drive Input** there if you are not running the full workflow.

---

## 9. Sync back to Google Drive

Push renamed files to the destination folder:

```bash
/opt/invoice-manager-core/project/scripts/sync-outgoing.sh
```

If you enabled archive sync, also run:

```bash
/opt/invoice-manager-core/project/scripts/sync-archive.sh
```

In the web UI, expand the **Advanced** panel in the **Process** tab and click **Push**, then **Clear Drive Input** when you are ready to remove the processed originals from the input folder.

---

## Typical monthly workflow

```bash
# 1. Pull new invoices from Google Drive
/opt/invoice-manager-core/project/scripts/sync-incoming.sh

# 2. Open UI and run the parser
#    http://<shared-pc-ip>:8000

# 3. Push results back
/opt/invoice-manager-core/project/scripts/sync-outgoing.sh
```

---

## Notes

- Keep `dry_run: true` while testing.
- `archive_folder` can be a relative path inside `output_folder` or an absolute path.
- Processed raw files remain in `incoming/` until you push outgoing and clear the Drive input folder.
- The example systemd service runs as user `invoice`. Create this user first or change `User=` to your own.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'invoice_parser'`

Make sure you ran `python -m pip install -e .` from `/opt/invoice-manager-core`.

### UI shows internal server error

Check the terminal or `journalctl -u invoice-manager` for the traceback. Common causes:

- Invalid JSON in `local/local_config.json`.
- `input_folder` or `output_folder` does not exist.
- Missing `invoice_parser` installation.

### rclone cannot access Shared drive

If using a service account, ensure:

- The service account was added to the **Shared drive itself**, not just a folder inside it.
- The service account has at least **Content manager** access.
- Your Workspace admin allows external accounts in Shared drives.

See [Service Account Setup](../../docs/SERVICE_ACCOUNT_SETUP.md) for details.

If using OAuth, ensure the configured Google account is a member of the Shared drive with at least **Editor** access.

### Process tab says "rclone not found"

Make sure rclone is installed and available in the PATH of the user running the UI.

### Process tab says sync is "Disabled"

Set `rclone.enabled` to `true` in `local/local_config.json`.
