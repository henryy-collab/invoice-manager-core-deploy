# Cheat Sheet — Invoice Manager Core

A quick reference for developing, running, and deploying the self-contained `invoice-manager-core` project.

This file is archived under `project/docs/`. Prefer the core README and `project/docs/AGENTS.md` for the most current instructions.

---

## Project layout

```
invoice-manager-core/
├── local/          # Python PDF parser package and CLI entry point
├── ui/             # FastAPI web UI and static frontend
├── docs/           # Core documentation for the current app
├── project/        # Archived reference docs, scripts and legacy guides
├── pyproject.toml  # installable packages: invoice_parser, invoice_ui
└── README.md
```

---

## Daily Git commands

| Command | Purpose |
|---|---|
| `git status` | See what files changed |
| `git diff` | See detailed line-by-line changes |
| `git add .` | Stage all changes for the next commit |
| `git commit -m "message"` | Save a snapshot |
| `git push` | Upload commits to GitHub |
| `git pull` | Download latest changes from GitHub |
| `git log --oneline -10` | Show last 10 commits |

### Typical edit cycle

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
git pull
# ... edit files ...
git status
git add .
git commit -m "Describe what you changed"
git push
```

---

## Set up a fresh machine

```powershell
cd "C:\Users\Henry Yau\Apps"
git clone https://github.com/henryy-collab/invoice-manager-core.git
cd invoice-manager-core
python -m pip install -e .
copy local\local_config.example.json local\local_config.json
# edit local\local_config.json with the correct folders
```

---

## Run the parser from command line

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
python local\parse_and_rename.py
```

Dry run:

```powershell
python local\parse_and_rename.py --dry-run
```

---

## Run the web UI

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
python ui\web_ui.py
```

Then open:

```
http://127.0.0.1:8000
```

The default tab is **Process**.

To change port or bind address:

```powershell
$env:INVOICE_UI_PORT = "8080"
python ui\web_ui.py
```

To point the UI at a different config file:

```powershell
$env:INVOICE_UI_CONFIG_PATH = "C:\...\local_config.json"
python ui\web_ui.py
```

---

## Using the Process tab

The **Process** tab is the main workflow:

1. Click **Process Invoices** in the Workflow panel header to run the full pipeline automatically: Pull → Preview → Rename → Write info to Report → Push → Clear Drive Input.
2. The flow pauses if it needs input or hits a problem:
   - **Manual review**: edit missing/incorrect fields in the preview table, then click **Resume Processing**.
   - **rclone not configured**: enable rclone and set the remote/source drive folder in the Config tab, then click **Resume Processing**.
   - **Google Sheets not configured**: set the spreadsheet URL and service account file in the Config tab, then click **Resume Processing**.
3. Click **Start Over** to reset the workflow. You can optionally clear the local incoming and/or outgoing folders at the same time.

The **Advanced** panel below the preview table contains individual step actions if you need to run Pull, Preview, Rename, Write info to Report, Push, Push Archive, or Clear Drive Input manually.

### Google Sheets report

Enable under `google_sheets` in `local/local_config.json`:

```json
{
  "google_sheets": {
    "enabled": true,
    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit",
    "service_account_file": "keys\\service-account.json",
    "tab_name_template": "%b %Y",
    "date_format": "%d/%m/%Y",
    "skip_existing_by": "number",
    "raw_sheet_suffix": " [Auto]",
    "protect_raw_sheets": true
  }
}
```

Relative paths for `service_account_file` are resolved from the project root.

Requirements:

- The service account must have **Editor** access to the spreadsheet.
- The **Google Sheets API** must be enabled in the same Google Cloud project.
- Click **Write info to Report** in the Advanced panel, or use **Process Invoices**.

A new tab named for the invoice month/year with an `[Auto]` suffix (e.g. `Apr 2026 [Auto]`) is created automatically. The first row shows a bold red warning; the header row is row 2. Each processed invoice writes one row with Client Ref., PDF Invoice No., PDF Invoice Date, Topped Currency and Topped amount. Existing invoice numbers are skipped.

### Files tab

The **Files** tab shows incoming and outgoing files in separate collapsible tables, plus the source/input/output folders and config path at the top.

### Config tab

The **Config** tab edits `local/local_config.json` from the browser. Save changes and the backend reloads the config automatically.

### Logs tab

The **Logs** tab shows recent processing events. Auto-refresh is enabled by default.

---

## Run tests

Parser tests:

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core\local"
python -m pytest
```

UI tests:

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core\ui"
python -m pytest
```

---

## Deploy to the shared PC

On the shared PC, open PowerShell and run:

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
git pull
python -m pip install -e .
# create local\local_config.json from the example if it doesn't exist yet
python ui\web_ui.py
```

Then access the UI from other machines via:

```
http://<shared-pc-ip>:8000
```

---

## Configuration

- Copy `local/local_config.example.json` to `local/local_config.json`.
- Edit `source_folder`, `input_folder`, `output_folder`, and other paths for that machine.
- `local/local_config.json` is ignored by Git — each PC keeps its own.

---

## What not to commit

These are already excluded in `.gitignore`:

- `local/local_config.json`
- `local/data/`
- `keys/*.json`
- `*.log`
- `__pycache__/`
- `.pytest_cache/`
- `desktop.ini`
- virtual environment folders

If `git status` shows files you didn’t mean to commit, check `.gitignore`.

---

## Branches (optional)

If you want to experiment without breaking `master`:

```powershell
git checkout -b my-experiment
# ... make changes ...
git add .
git commit -m "Experimental change"
git checkout master
```

To merge the experiment back:

```powershell
git checkout master
git merge my-experiment
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'invoice_parser'`

Run from repo root:

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"
python -m pip install -e .
```

### `Could not find local/local_config.json`

Create it from the example:

```powershell
cd local
copy local_config.example.json local_config.json
```

Then edit `source_folder` and other paths.

### UI shows internal server error

Check the terminal running `python ui\web_ui.py` for the traceback. Common causes:

- Invalid JSON in `local/local_config.json`
- `input_folder` or `output_folder` path does not exist
- Missing `invoice_parser` installation

### Changes I made in a Google Drive folder are gone

The app now works from `local/data/` on disk. Do all editing in `local/data/incoming/` and `local/data/outgoing/` through the UI, or configure rclone to sync from a Shared drive input folder.

---

## Quick command summary

```powershell
# Start here every time
cd "C:\Users\Henry Yau\Apps\invoice-manager-core"

# Get latest code
git pull

# Run parser
cd local
python parse_and_rename.py
cd ..

# Run UI
python ui\web_ui.py

# Save your work
git add .
git commit -m "What changed"
git push
```
