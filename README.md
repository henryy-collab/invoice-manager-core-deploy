# Invoice Manager Core

Self-contained invoice PDF parser and renamer with a browser-based UI.

## What it is

- `local/invoice_parser/` — Python PDF parser package.
- `local/parse_and_rename.py` — command-line entry point.
- `ui/invoice_ui/` — FastAPI web UI package.
- `ui/web_ui.py` — web UI launcher.
- `local/data/` — runtime data folder (created automatically, excluded from Git).

## Quick start

### 1. Install

From the repo root:

```powershell
python -m pip install -e .
```

### 2. Configure

Copy the example config:

```powershell
cd local
copy local_config.example.json local_config.json
cd ..
```

Edit `local/local_config.json` if you want to change paths. By default all data folders live inside `local/data/`.

### 3. Run the web UI

```powershell
python ui\web_ui.py
```

Open http://127.0.0.1:8000.

### 4. Or run from the command line

```powershell
cd local
python parse_and_rename.py
```

Use `--dry-run` to preview changes without modifying files.

## Tests

```powershell
cd local
python -m pytest
cd ..\ui
python -m pytest
```

## Optional Google Drive sync

To push processed files to a Google Shared drive, configure a service account and rclone. See `docs/SERVICE_ACCOUNT_SETUP.md`.

## Deployment

For Coolify deployment instructions, see `docs/DEPLOYMENT.md`.

Release workflow:

- Source of truth: `henryy-collab/invoice-manager-core`.
- Deployment mirror: `FirstPage-Glass/invoice-manager-core`.
- Coolify auto-deploys from the deployment mirror's `master` branch.
- To release: `git checkout master && git pull && git push glass master`.

## Data layout

`local/data/` is created automatically on startup:

```
local/data/
├── incoming/     ← raw PDFs
├── outgoing/     ← renamed PDFs + .meta.json sidecars
├── archive/      ← optional originals backup
├── logs/         ← parse_and_rename.log
├── reports/      ← CSV exports
└── state/        ← last_run_processed.json
```

`local/data/` is excluded from Git.

## Notes

- `local/local_config.json` is machine-specific and gitignored — it never gets committed. Copy `local/local_config.example.json` on each machine and edit that copy.
- The UI has no authentication; run it only on a trusted network.
- After UI updates, hard-refresh the browser (`Ctrl+F5`) to clear cached assets.
