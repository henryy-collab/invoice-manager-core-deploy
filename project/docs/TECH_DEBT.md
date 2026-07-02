# Technical Debt & Architecture Review

Analysis date: 2026-06-24

Scope: Python parser (`local/`), FastAPI UI (`ui/`), project documentation, and archived Google Apps Script (`project/`) documentation.

---

## Executive summary

The codebase is reasonably well-organised for its current size. The top-level split between `local/`, `ui/`, `v2/`, and `docs/` is clean, and the parser follows a modular design. As the project grows, however, several issues are becoming apparent: domain logic is duplicated across modules, the UI depends on private parser internals, the frontend orchestrates a multi-step business process, and the test runner requires manual `PYTHONPATH` setup. Addressing the high-priority items first will make future feature work safer and faster.

Top priorities:

1. Unify the report column schemas used by CSV and Google Sheets.
2. Remove the duplicated `missing_required_fields` implementation.
3. Stop the UI from importing private functions from `invoice_parser.processor`.

---

## Strengths

- Clear top-level separation of concerns between `local/`, `ui/`, `docs/`, and `project/`.
- Parser is modular: extractor, parsers, filename, files, processor, config.
- Pydantic-based configuration with regex validation.
- Lightweight vanilla-JS frontend with no build step.
- Core parser and UI backend have test coverage (82 tests pass when run correctly).

---

## Findings

### High priority

| # | Issue | Location | Impact | Recommended fix |
|---|---|---|---|---|
| 1 | **Duplicated `missing_required_fields`** | `local/invoice_parser/parsers/invoice.py:21-33` and `local/invoice_parser/files.py:19-31` | Two implementations of the same logic. Risk of divergence and confusion about which one is authoritative. | Keep one canonical version. `files.py` is already used by `processor.py` and tests; remove the version in `parsers/invoice.py` or move both to a shared validation module. |
| 2 | **Report column schemas diverged** | `local/invoice_parser/reports/sheets.py:10-26` (16 columns) and `ui/invoice_ui/services/reports_service.py:27-42` (14 columns, different names/order) | CSV and Google Sheets reports represent the same domain but expose different columns. Easy for them to drift further. | Define a single canonical report schema in `invoice_parser/reports/` and reuse it for both CSV and Sheets outputs. Align `Invoice Date` / `PDF Invoice Date` semantics after deciding the intended mapping. Partially addressed: `Topped Currency` was added to both schemas. |
| 3 | **UI imports private parser internals** | `ui/invoice_ui/services/parse_service.py:17-22` imports `_resolve_target_name` and `_write_run_state` from `invoice_parser.processor` | Leaky abstraction. Changes to `processor.py` internals can break the UI. | Expose public equivalents in `invoice_parser.processor` (e.g. `resolve_target_name`, `write_run_state`) or move preview/update/run orchestration into `invoice_parser` so the UI calls a stable API. |
| 4 | **Global in-memory preview state** | `ui/invoice_ui/services/parse_service.py:32` (`_last_results`) | Preview results are shared across all requests/threads. Acceptable for a single-user trusted-network tool, but not concurrent-safe and would break under multiple users. | Short term: document the limitation. Long term: store preview state per session or request, or move end-to-end processing to a backend job queue. |
| 5 | **Frontend orchestrates end-to-end pipeline** | `ui/static/js/features/local/workflow.js:93-155` | Business process sequencing lives in the browser, making it harder to test, retry, or reason about transaction boundaries. | Add a backend endpoint such as `POST /api/process/end-to-end` that runs the pipeline server-side. The frontend calls it once and displays progress/errors. |

### Medium priority

| # | Issue | Location | Impact | Recommended fix |
|---|---|---|---|---|
| 6 | **`sync_service.py` has mixed responsibilities** | `ui/invoice_ui/services/sync_service.py` (299 lines) | Handles rclone subprocess calls, local cleanup, metadata reading, and subfolder templating in one file. | Split into focused modules: `rclone_runner.py`, `metadata.py`, `subfolder.py`, with `sync_service.py` as a thin orchestrator. |
| 7 | **UI package not installable** | `pyproject.toml` only declares `local/` package | ~~`pytest` from the repo root fails unless `PYTHONPATH` includes `ui/`. New contributors will hit this.~~ **Resolved**: `pyproject.toml` now includes both `local/` and `ui/` packages. | — |
| 8 | **File-download route in `main.py`** | `ui/invoice_ui/main.py:47-66` | Routing logic is split between routers and `main.py`. | Move the download endpoint into `files_router.py`. |
| 9 | **No linting, formatting, or type-checking** | `pyproject.toml` lacks `ruff`, `black`, `mypy`, etc. | Style inconsistencies and type errors will creep in as the codebase grows. | Add `ruff` and `mypy` configuration to `pyproject.toml`. Optionally run them in CI or as a pre-commit check. |

### Low priority / polish

| # | Issue | Location | Impact | Recommended fix |
|---|---|---|---|---|
| 10 | **No frontend tests** | `ui/static/js/` | JavaScript logic for `api.js`, `utils.js`, and `workflow.js` is untested. | Add a lightweight JS test runner such as Vitest or Jest for critical utilities. |
| 11 | **Single large stylesheet** | `ui/static/css/styles.css` (647 lines) | Fine now, but may become hard to navigate if the UI grows. | Consider splitting into component or feature-level CSS files once it exceeds ~800-1000 lines. |
| 12 | **`desktop.ini` files in working tree** | Multiple directories | Already `.gitignore`d, but present locally and occasionally appear in listings. | Delete them from the working tree. |
| 13 | **`ArchiveConfig.mode` over-engineered** | `local/invoice_parser/config.py:121-123` | Only `"copy_original"` is supported. | Either add more modes or simplify to a boolean/feature flag. |
| 14 | **Filename collision logic duplicated across runtimes** | `local/invoice_parser/filename.py:37-60` vs `v2/FilenameResolver.gs:1-35` | Python and GAS implementations can drift. | Document the canonical algorithm and keep the GAS version as a minimal, manually synced port. |

---

## Recommended action order

1. **Unify report column schemas** — low risk, high consistency payoff.
2. **Remove duplicated `missing_required_fields`** — reduces maintenance surface.
3. **Make the UI package installable or document `PYTHONPATH`** — improves contributor experience.
4. **Move file-download route to `files_router.py`** — small cleanup.
5. **Expose public parser APIs** instead of private imports — improves abstraction.
6. **Add linting/type-checking** — prevents future drift.
7. **Refactor `sync_service.py`** — improves testability.
8. **Backend-driven end-to-end pipeline** — larger change, but improves reliability and testability.

---

## Test notes

- All 82 tests pass when run from the repo root:
  ```powershell
  python -m pytest local\tests ui\tests
  ```
- No tests exist for archived Google Apps Script code or frontend JavaScript.
- No tests cover `sync_service.py` rclone interactions because they shell out to an external binary.

---

## Documentation notes

- `docs/AGENTS.md` references this file under "Quick reference".
- When any item above is fixed, update `CHANGELOG.md` and any affected setup guide.
- `project/docs/MACOS_SETUP.md` has been deprecated; consider removing it entirely once the rclone/service-account setup is proven stable.
