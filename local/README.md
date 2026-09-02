# Local Invoice Parser and Renamer

This Python script reads PDF invoices, extracts key fields using **PyMuPDF**, and renames the files.

## What it does

- Scans a configured source folder for PDFs.
- Extracts text from each PDF with PyMuPDF (fast, low memory, no external AI models).
- Classifies each PDF to a configured **document type** and parses account, account ID, invoice number, invoice date, total amount, and currency using per-type regex patterns.
- Extracts a **per-account breakdown** (`accounts`) linking each account name to its own account ID and amount. Multi-account invoices (e.g. consolidated HKCT invoices) are parsed from the "Summary of costs by account budget" table; single-account invoices produce one record with the invoice total. The breakdown is stored in the `.meta.json` sidecar.
- Renames files based on a per-document-type filename template.
- Uses the original filename as the invoice number if the PDF text does not contain it (configurable).
- Falls back to `000_<original>.pdf` when configured required fields cannot be found, so manual-review files sort to the top.
- Copies the **original** PDF to an `archive/` subfolder before renaming (configurable).
- Supports a `--dry-run` flag to preview changes without touching files.
- Writes JSON logs to `parse_and_rename.log`.
- Can append extracted invoice fields to a Google Sheets report (configured separately in `local_config.json`).
- Can upload extracted invoice fields to a NocoDB `Invoices` table from the `.meta.json` sidecars (`upload_nocodb.py`).

## Why PyMuPDF instead of Docling

Docling consistently hit `std::bad_alloc` errors during layout preprocessing on these 2-page Google invoices, truncating the extracted text and losing the account name. PyMuPDF reads all pages reliably and is much faster.

## Setup

1. Ensure Python 3.11+ is installed (tested on 3.14.4).
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Copy `local_config.example.json` to `local_config.json` and edit paths if needed.

## Configuration

`local_config.json` (copy from `local_config.example.json`) is organised into global settings and a `document_types` registry.

### Global settings

```json
{
  "source_folder": "local/data",
  "input_folder": "local/data/incoming",
  "output_folder": "local/data/outgoing",
  "archive_folder": "local/data/archive",
  "log_file": "local/data/logs/parse_and_rename.log",
  "timezone": "Asia/Hong_Kong",
  "default_document_type": "googleadsinvoice",

  "features": {
    "archive": true,
    "skip_already_processed": true,
    "number_fallback_to_filename": true,
    "deduplicate_within_run": true,
    "dry_run": false
  },

  "filename": {
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

- `source_folder`, `input_folder`, `output_folder`, `archive_folder`, `log_file`: relative paths are resolved from the **project root** (the directory containing `.git`).
- `default_document_type`: the document type used when no classifier pattern matches.
- `features`: global processing behaviour.
- `filename`: global manual-review prefix, already-processed patterns, and collision suffix.

### Document types

Each entry under `document_types` describes how to recognise and parse one kind of document:

```json
{
  "document_types": {
    "googleadsinvoice": {
      "classifier": {
        "patterns": ["Invoice", "Invoice number", "Invoice date"]
      },
      "fields": {
        "account": {
          "parser": "account",
          "patterns": [
            {"regex": "^Account:\\s*(.+?)(?=\\s*\\[|\\s*$)", "group": 1, "flags": ["IGNORECASE", "MULTILINE"]}
          ],
          "unknown_values": ["-", "—", "--", "N/A", "n/a"],
          "fallback": "UNKNOWN"
        },
        "account_id": {
          "parser": "account_id",
          "patterns": [
            {"regex": "Account:\\s*[^\\[]*?\\[([\\d\\-]+)\\]", "group": 1, "flags": ["IGNORECASE"]},
            {"regex": "Account\\s*ID[:\\s]+([\\d\\-]+)", "group": 1, "flags": ["IGNORECASE"]}
          ],
          "unknown_values": ["-", "—", "--", "N/A", "n/a"],
          "fallback": "UNKNOWN"
        },
        "accounts": {
          "parser": "accounts",
          "summary_marker_regex": "Summary\\s+of\\s+costs\\s+by\\s+account\\s+budget",
          "amount_header_regex": "^Amount\\s*\\(?[A-Z$€£¥]*\\)?$",
          "account_line_regex": "^Account:\\s*(.+?)(?=\\s*\\[|\\s*$)",
          "account_id_line_regex": "Account\\s*ID[:\\s]+([\\d\\-]+)",
          "total_label_regex": "(Total\\s*amount\\s*due\\s*in|Total\\s+in)\\s+[A-Z]{3}",
          "amount_regex": "(-?)(?:HK\\$|US\\$|\\$|€|£|¥|SGD|HKD|USD|AUD|GBP|EUR|JPY)?\\s*(-?[\\d,]+\\.\\d{2})",
          "id_lookahead": 4,
          "name_max_lines": 3
        },
        "number": {
          "parser": "number",
          "patterns": [
            {"regex": "Invoice\\s*number[:\\s]+([A-Z0-9\\-]+)", "group": 1, "flags": ["IGNORECASE"]}
          ],
          "require_digit": true,
          "fallback_to_filename": true,
          "filename_pattern": "^\\d+$"
        },
        "date": {
          "parser": "date",
          "parse_formats": ["%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"],
          "nearby_line_window": 2,
          "details_block": {
            "enabled": true,
            "header": "Details",
            "dot_separator_regex": "^\\.{5,}$",
            "label_regex": "Invoice\\s*number|Invoice\\s*date|Payment\\s*terms|Billing\\s*ID|Account\\s*ID",
            "max_label_length": 80
          }
        },
        "currency": {
          "parser": "currency",
          "primary_regex": "Total\\s*amount\\s*due\\s*in\\s*([A-Z]{3})",
          "symbol_map": {"HK$": "HKD", "US$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY"}
        },
        "total": {
          "parser": "total",
          "primary_regex": "",
          "primary_regexes": [
            "Total\\s*amount\\s*due(?:\\s*in\\s*[A-Z]{3})?[:\\s]*([A-Z$€£¥]*)\\s*(-?[\\d,]+\\.\\d{2})",
            "Total\\s+in\\s+[A-Z]{3}[:\\s]*(-?)([A-Z$€£¥]*)\\s*(-?[\\d,]+\\.\\d{2})"
          ],
          "fallback_regex": "(-?)(?:HK\\$|US\\$|\\$|€|£|¥)\\s*(-?[\\d,]+\\.\\d{2})",
          "pick_max": true
        }
      },
      "filename_template": "{account}_{number}_Invoice_{date}.pdf",
      "placeholders": {
        "account": {"sanitize": true, "fallback": "UNKNOWN"},
        "account_id": {"sanitize": true, "fallback": "unknown"},
        "number": {"sanitize": true, "fallback": "unknown"},
        "date": {"fallback": "unknown-date"},
        "total": {"fallback": "unknown"},
        "currency": {"fallback": "unknown"}
      },
      "manual_review_for_missing": ["account", "date"],
      "report_columns": {
        "account": "Client Ref.",
        "date": "PDF Invoice Date",
        "number": "PDF Invoice No.",
        "currency": "Topped Currency",
        "total": "Topped amount"
      }
    }
  }
}
```

Per-document-type sections:

- `classifier`: regex patterns used to decide whether a PDF belongs to this document type.
- `fields`: parser configuration for each field. The `parser` key selects the strategy (`account`, `account_id`, `accounts`, `number`, `date`, `currency`, `total`, or custom). Other keys are passed through to that parser.
- `filename_template`: output filename pattern; supports `{account}`, `{account_id}`, `{number}`, `{date}`, `{total}`, `{currency}`.
- `placeholders`: fallback values and sanitisation flags used when building the filename.
- `manual_review_for_missing`: fields that must be present; missing any triggers the manual-review prefix.
- `report_columns`: maps fields to fixed CSV/Google Sheets column headers.
- `accounts`: a structured breakdown written to the `.meta.json` sidecar only (not used in filenames or reports). It parses the "Summary of costs by account budget" table for multi-account invoices, aggregates budget rows by account ID, and falls back to a single account record with the invoice total when no such table exists.

### Total parser

The total parser first looks for a `Total amount due in <CURRENCY>` or `Total in <CURRENCY>` header and returns the **last amount** in the following block. This handles Google invoice PDFs where column layout reorders lines during text extraction, including credit notes with negative totals. If no header block is found, it falls back to the configured regexes.

### Feature flags

| Flag | Default | Description |
|---|---|---|
| `archive` | `true` | Copy the original PDF to the archive folder before renaming. |
| `skip_already_processed` | `true` | Skip files matching the processed filename patterns. |
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

### Upload parsed invoices to NocoDB

After processing, upload the `.meta.json` sidecars (in `output_folder`) to a NocoDB `Invoices` table:

```powershell
python upload_nocodb.py --dry-run   # preview payloads without uploading
python upload_nocodb.py             # upload
```

Configuration lives in the `nocodb` section of `local_config.json`:

```json
{
  "nocodb": {
    "enabled": true,
    "base_id": "pk5ing4mu06vtd6",
    "table_id": "md8v02ty4emzxzn",
    "column_map": {
      "account": "ad_account_name",
      "account_id": "account_id",
      "number": "pdf_invoice_number",
      "date": "pdf_invoice_date",
      "total": "topped_amount",
      "currency": "currency",
      "source": "source"
    }
  }
}
```

Environment variables (gitignored, in `.env`):

- `NOCODB_TOKEN` — the NocoDB API token (`xc-token` header).
- `NOCODB_URL` — NocoDB base URL (default `http://localhost:3000`). For a deployed container, use a URL reachable from the server, not `localhost`.

Notes:

- `source` is a dropdown column in NocoDB; the app does not parse a source value yet, so it is uploaded as empty.
- Use `--dry-run` first to confirm the payload mapping before uploading for real.

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
- Files missing any configured required fields are renamed to `000_<original>.pdf` for manual review.
