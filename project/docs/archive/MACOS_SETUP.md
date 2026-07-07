> **Deprecated**: this guide is no longer maintained. The recommended setup is now the rclone/service-account approach described in [`SERVICE_ACCOUNT_SETUP.md`](SERVICE_ACCOUNT_SETUP.md) and [`LINUX_SHARED_SETUP.md`](LINUX_SHARED_SETUP.md). Google Drive for Desktop setups may continue to work but are not actively supported.

# macOS Local Setup

Guide for running Invoice Manager Core locally on macOS with Google Drive for Desktop.

---

## Overview

```
Google Shared Drive
├── InvoicesRAW/                    ← GAS downloader saves raw PDFs here
└── Invoices/                       ← processed files end up here

        ↑↓  Google Drive for Desktop sync
~/invoice-manager-data/
├── incoming/                       ← synced copy of InvoicesRAW
├── outgoing/                       ← files to sync to Invoices
├── archive/                        ← local backup of originals
└── logs/                           ← app logs
```

The app never touches Google Drive directly. It only reads/writes local files. Google Drive for Desktop handles the sync.

---

## Prerequisites

- macOS 12 or later
- Python 3.11+ installed
- Google Drive for Desktop installed and signed in
- Access to the Shared drive containing `InvoicesRAW` and `Invoices`

---

## 1. Install Google Drive for Desktop

Download and install from:

```
https://www.google.com/drive/download/
```

Sign in with the Google account that has access to the Shared drive.

In Google Drive for Desktop preferences, enable:

- **Stream files** or **Mirror files** for the Shared drive.
- Sync the Shared drive that contains `InvoicesRAW` and `Invoices`.

After syncing, the folders will appear locally. The exact path depends on your setup, often something like:

```
~/Google Drive/Shared drives/<Drive Name>/InvoicesRAW
~/Google Drive/Shared drives/<Drive Name>/Invoices
```

Note the full paths for the next step.

---

## 2. Create local working folders

```bash
mkdir -p ~/invoice-manager-data/{incoming,outgoing,archive,logs}
```

You can also point `incoming/` and `outgoing/` directly at the Google Drive for Desktop synced folders. In that case you do not need separate `incoming/` and `outgoing/` folders.

---

## 3. Install the app

```bash
cd ~/Apps
git clone https://github.com/henryy-collab/invoice-manager-core.git
cd invoice-manager-core
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

---

## 4. Configure

Copy the example config and edit it:

```bash
cp local/local_config.example.json local/local_config.json
```

Edit `local/local_config.json`:

```json
{
  "source_folder": "/Users/YOUR_USERNAME/invoice-manager-data",
  "input_folder": "/Users/YOUR_USERNAME/Google Drive/Shared drives/YOUR_DRIVE_NAME/InvoicesRAW",
  "output_folder": "/Users/YOUR_USERNAME/Google Drive/Shared drives/YOUR_DRIVE_NAME/Invoices",
  "archive_folder": "/Users/YOUR_USERNAME/invoice-manager-data/archive",
  "log_file": "/Users/YOUR_USERNAME/invoice-manager-data/logs/parse_and_rename.log",
  "timezone": "Asia/Hong_Kong",

  "features": {
    "archive": true,
    "skip_already_processed": true,
    "manual_review_for_missing": ["account", "date"],
    "number_fallback_to_filename": true,
    "deduplicate_within_run": true,
    "dry_run": false
  },

  "rclone": {
    "enabled": false,
    "remote": "mydrive-shared",
    "source_drive_folder": "Auto Email Management/Google Ads/InvoicesRAW",
    "destination_drive_folder": "Auto Email Management/Google Ads/Invoices",
    "archive_drive_folder": null
  }
}
```

Important:

- Replace `YOUR_USERNAME` and the Drive paths with your actual values.
- Set `input_folder` to the synced `InvoicesRAW` folder.
- Set `output_folder` to the synced `Invoices` folder.
- Keep `rclone.enabled` as `false` on macOS if using Google Drive for Desktop.

### Folder paths for rclone

If you switch from Google Drive for Desktop to rclone later, `source_drive_folder` and `destination_drive_folder` are paths within your Google Drive or Shared drive, relative to the root. Use forward slashes for nested folders.

---

## 5. Run the web UI

```bash
source .venv/bin/activate
python ui/web_ui.py
```

Open in a browser:

```
http://127.0.0.1:8000
```

The default tab is **Process**.

---

## 6. Typical workflow

1. Wait for Google Drive for Desktop to sync new raw invoices into `InvoicesRAW`.
2. Open the UI and go to **Files** to confirm the PDFs appear.
3. Open the **Process** tab, click **Preview**, then edit any missing fields inline.
4. Click **Save Edits**, then **Rename Files**.
5. Renamed files appear in the `Invoices` folder locally.
6. Wait for Google Drive for Desktop to sync the renamed files back to the Shared drive.

---

## Notes

- This setup uses **Google Drive for Desktop**, not rclone. The sync actions in the **Process** tab are intended for rclone and can be left disabled.
- The archive folder stays local only. If you want to back it up to Google Drive, either place it inside a synced Drive folder or switch to the rclone setup in `docs/LINUX_SHARED_SETUP.md`.
- Keep `dry_run: true` while testing.
- Processed raw files remain in `incoming/` until the next run pulls fresh files. Manage `InvoicesRAW` manually if using Google Drive for Desktop.

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'invoice_parser'`

Make sure you ran `python -m pip install -e .` from the repo root and activated the virtual environment.

### Files tab shows no files

Check that Google Drive for Desktop has finished syncing and that `input_folder` points to the correct local path.

### UI shows internal server error

Check the terminal for the traceback. Common causes:

- Invalid JSON in `local/local_config.json`
- `input_folder` or `output_folder` does not exist
- Missing `invoice_parser` installation

### `local/local_config.json` not found

Create it by copying the example:

```bash
cp local/local_config.example.json local/local_config.json
```

Then edit the paths.

