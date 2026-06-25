# Local Invoice Parser and Renamer

This Python script reads PDF invoices downloaded by the Google Apps Script downloader, extracts key fields using **PyMuPDF**, and renames the files.

## What it does

- Scans a configured source folder for PDFs.
- Extracts text from each PDF with PyMuPDF (fast, low memory, no external AI models).
- Parses account, invoice number, invoice date, total amount, and currency using configurable regex patterns.
- Renames files to `{account}_{number}_Invoice_{date}.pdf`.
- Uses the original filename as the invoice number if the PDF text does not contain it (configurable).
- Falls back to `000_<original>.pdf` when configured required fields cannot be found, so manual-review files sort to the top.
- Copies the **original** PDF to an `archive/` subfolder before renaming (configurable).
- Supports a `--dry-run` flag to preview changes without touching files.
- Writes JSON logs to `parse_and_rename.log`.
- Can append extracted invoice fields to a Google Sheets report (configured separately in `local_config.json`).

## Why PyMuPDF instead of Docling

Docling consistently hit `std::bad_alloc` errors during layout preprocessing on these 2-page Google invoices, truncating the extracted text and losing the account name. PyMuPDF reads all pages reliably and is much faster.

## Setup

1. Ensure Python 3.11+ is installed (tested on 3.14.4).
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Copy `local_config.example.json` to `local_config.json` and edit `source_folder` to point at your synced Drive folder.

## Configuration

`local_config.json` (copy from `local_config.example.json`):

```json
{
  "source_folder": "G:\\\\...\\\\Test Destination",
  "filename_template": "{account}_{number}_Invoice_{date}.pdf",
  "date_format": "%Y%m%d",
  "archive_folder": "archive",
  "log_file": "parse_and_rename.log",
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

  "parsers": {
    "account": {
      "patterns": [
        {"regex": "^Account:\\\\s*(.+?)(?=\\\\s*\\\\[|\\\\s*$)", "group": 1, "flags": ["IGNORECASE", "MULTILINE"]},
        {"regex": "Account\\\\s*ID[:\\\\s]+([\\\\d\\\\-]+)", "group": 1, "flags": ["IGNORECASE"]}
      ],
      "unknown_values": ["-", "—", "--", "N/A", "n/a"],
      "fallback": "UNKNOWN"
    },
    "number": {
      "patterns": [
        {"regex": "Invoice\\\\s*number[:\\\\s]+([A-Z0-9\\\\-]+)", "group": 1, "flags": ["IGNORECASE"]}
      ],
      "require_digit": true,
      "fallback_to_filename": true,
      "filename_pattern": "^\\\\d+$"
    },
    "date": {
      "parse_formats": ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"],
      "nearby_line_window": 2,
      "details_block": {
        "enabled": true,
        "header": "Details",
        "dot_separator_regex": "^\\\\.{5,}$",
        "label_regex": "Invoice\\\\s*number|Invoice\\\\s*date|Payment\\\\s*terms|Billing\\\\s*ID|Account\\\\s*ID|Tax\\\\s*Invoice",
        "max_label_length": 80
      }
    },
    "currency": {
      "primary_regex": "Total\\\\s*amount\\\\s*due\\\\s*in\\\\s*([A-Z]{3})",
      "symbol_map": {"HK$": "HKD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
    },
    "total": {
      "primary_regex": "Total\\\\s*amount\\\\s*due(?:\\\\s*in\\\\s*[A-Z]{3})?[:\\\\s]*([A-Z$€£¥]*)\\\\s*([\\\\d,]+\\\\.\\\\d{2})",
      "fallback_regex": "(?:HK\\\\$|US\\\\$|\\\\$|€|£|¥)\\\\s*([\\\\d,]+\\\\.\\\\d{2})",
      "pick_max": true
    }
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
      "_Invoice_\\\\d{8}\\\\.pdf$",
      "_unparsed\\\\.pdf$",
      "^000_"
    ],
    "collision_suffix": "_{counter}"
  }
}
```

- `source_folder`: root data folder. Other folders can be set relative to this.
- `input_folder`: folder where unprocessed invoice PDFs are placed before running.
- `output_folder`: folder where renamed invoice PDFs are saved after running.
- `filename_template`: output filename pattern; supports `{account}`, `{number}`, `{date}`, `{total}`, `{currency}`.
- `date_format`: Python `strftime` format used for the `{date}` part of the output filename.
- `archive_folder`: folder to copy original PDFs into when archiving is enabled.
- `log_file`: path to JSON log file.

### Feature flags

| Flag | Default | Description |
|---|---|---|
| `archive` | `true` | Copy the original PDF to the archive folder before renaming. |
| `skip_already_processed` | `true` | Skip files matching the processed filename patterns. |
| `manual_review_for_missing` | `["account", "date"]` | Fields that must be present; missing any triggers the manual-review prefix. |
| `number_fallback_to_filename` | `true` | Use the original filename as the invoice number when not found in the PDF text. |
| `deduplicate_within_run` | `true` | Append `_1`, `_2`, etc. when the same target name is generated twice in one run. |
| `dry_run` | `false` | When `true`, log intended actions without modifying files or creating directories. |

## Usage

### Process all PDFs in the source folder

```powershell
python parse_and_rename.py
```

You can also run the package module directly:

```powershell
python -m invoice_parser.cli
```

### Process a single test file

```powershell
python parse_and_rename.py "G:\...\Test Destination\5593369279.pdf"
```

### Preview changes without modifying files

```powershell
python parse_and_rename.py --dry-run
```

In dry-run mode the script logs every intended rename and archive copy but does **not** create directories, copy files, or rename anything. You can combine it with a single test file:

```powershell
python parse_and_rename.py "G:\...\Test Destination\5593369279.pdf" --dry-run
```

## Web UI

A browser-based UI is available for team use. See the main project `README.md` for details.

Start it from the repo root with:

```powershell
python ui\web_ui.py
```

Then open `http://<shared-pc-ip>:8000` in a browser.

In the **Process** tab, click **Process Invoices** to run the full workflow automatically. The flow pauses if files need manual review or a config step is missing, then resumes from that step. Individual steps are available in the Advanced panel.

## Tests

Run the test suite with pytest from inside the `local/` folder:

```powershell
cd local
python -m pytest
```

Or with verbose output:

```powershell
cd local
python -m pytest -v
```

## Output

- Successfully parsed files are renamed in the source folder.
- The **original** PDF is copied to `archive/` before renaming (when `features.archive` is `true`).
- Files missing any configured required fields are renamed to `000_\u003coriginal\u003e.pdf` for manual review.
- Check `parse_and_rename.log` for detailed JSON events.

## Notes

- Already-renamed files and `000_` files are skipped on subsequent runs (when `features.skip_already_processed` is `true`).
- The script does not delete originals; it copies them to the archive folder before renaming.
- The date parser specifically handles Google's invoice layout where values appear above the `Details` header and labels appear below it.
- Parser regexes, date formats, and the currency symbol map can be customized in `local_config.json` without changing code.
- Google Sheets reporting is configured in `local_config.json` under `google_sheets`. See the main project documentation for setup.

