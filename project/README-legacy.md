> **Deprecated**: this README is from the original `invoice-manager` repo and is kept here for reference only. Active development continues in `invoice-manager-core`. See the core `README.md` for the current quick-start guide.

# Invoice Manager (legacy)

A small system for processing Google invoice PDFs:

- **`local/`** — local PDF parser and renamer (Python).
- **`ui/`** — web UI for running the parser from a browser (FastAPI + vanilla JS).
- **`v2/`** — Google Apps Script downloader that saves attachments to Drive (not included in core).

## Quick start

### 1. Install the parser package

From the repo root:

```powershell
python -m pip install -e .
```

This makes `invoice_parser` importable by both the CLI and the UI.

### 2. Configure the parser

Copy the example config and edit `source_folder` to point at your invoice folder:

```powershell
cd local
copy local_config.example.json local_config.json
```

### 3. Run from the command line

```powershell
cd local
python parse_and_rename.py
```

### 4. Run the web UI

From the repo root:

```powershell
cd "C:\Users\Henry Yau\Apps\invoice-manager"
python ui\web_ui.py
```

Then open `http://127.0.0.1:8000`. The default tab is **Process**.

To use a different config file:

```powershell
$env:INVOICE_UI_CONFIG_PATH = "C:\Path\To\local_config.json"
python ui\web_ui.py
```

## UI overview

The web UI has four tabs:

- **Process** — the main workflow tab. Click **Process Invoices** to run Pull → Preview → Rename → Write info to Report → Push → Clear automatically. The flow pauses if files need review or a config step is missing, then resumes from that step. Individual steps are available in the Advanced panel.
- **Files** — view files in the incoming and outgoing folders, with their status, size, and download links. The folder paths and config location are shown at the top.
- **Config** — edit `local_config.json` from the browser.
- **Logs** — view recent processing events.

## Platform setup guides

- [Linux shared PC with rclone and service account](docs/SERVICE_ACCOUNT_SETUP.md) (recommended)
- [Linux shared PC with rclone](docs/LINUX_SHARED_SETUP.md)
- [macOS local with Google Drive for Desktop](docs/MACOS_SETUP.md) (deprecated)

## Changelog

See [docs/CHANGELOG.md](docs/CHANGELOG.md) for a history of merged features.

## Folder layout

```
invoice-manager/
├── .gitignore
├── pyproject.toml
├── README.md
├── local/
│   ├── invoice_parser/       # parser package
│   ├── parse_and_rename.py   # CLI entry point
│   ├── local_config.example.json
│   ├── requirements.txt
│   └── tests/
├── ui/
│   ├── invoice_ui/           # FastAPI app package
│   ├── static/               # frontend assets
│   │   └── js/
│   │       ├── core/         # api, utils, app router
│   │       └── features/
│   │           ├── local/    # files.js, workflow.js, config.js, logs.js
│   │           └── shared/   # modal.js
│   ├── web_ui.py             # UI launcher
│   ├── requirements.txt
│   └── tests/
└── v2/
    └── ...                   # Google Apps Script files
```

## Notes

- The UI expects `local/local_config.json` by default. Point elsewhere with `INVOICE_UI_CONFIG_PATH`.
- Keep `local/local_config.json` and log files out of Git; they are excluded in `.gitignore`.
- No authentication on the UI — run it only on a trusted network.
- After UI updates, hard-refresh the browser (`Ctrl+F5`) so the latest CSS and JS are loaded.
