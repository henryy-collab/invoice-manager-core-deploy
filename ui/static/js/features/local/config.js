const configModule = {
  originalConfig: null,

  async load() {
    try {
      const data = await api.config();
      this.originalConfig = data.config;
      this.render(data.config);
      this.showError("");
      this.showSuccess("");
    } catch (err) {
      this.showError("Failed to load config: " + err.message);
    }
  },

  render(cfg) {
    const form = document.getElementById("config-form");
    form.innerHTML = "";

    form.appendChild(section("Folders", [
      textField("Root data folder", "source_folder", cfg.source_folder, "Base folder for invoice data. Other folders can be set relative to this."),
      textField("Raw invoices folder", "input_folder", cfg.input_folder, "Folder where unprocessed invoice PDFs are placed before running."),
      textField("Processed invoices folder", "output_folder", cfg.output_folder, "Folder where renamed invoice PDFs are saved after running."),
      textField("Archive folder", "archive_folder", cfg.archive_folder, "Where original PDF copies are stored when archiving is enabled."),
      textField("Log file", "log_file", cfg.log_file, "Where processing events are written."),
      textField("Timezone", "timezone", cfg.timezone, "Timezone used for timestamps in logs and reports."),
    ]));

    form.appendChild(section("Output filename", [
      textField("Filename pattern", "filename_template", cfg.filename_template, "How renamed files are named. Use {account}, {number}, {date}, {total}, {currency}."),
      textField("Output date format", "date_format", cfg.date_format, "Format for the {date} part of the output filename, e.g. %Y%m%d."),
    ]));

    const features = cfg.features || {};
    form.appendChild(section("Processing behaviour", [
      checkboxField("Keep copies of original PDFs", "features.archive", features.archive, "When enabled, copies each raw PDF to the archive folder before renaming."),
      checkboxField("Skip files that look already processed", "features.skip_already_processed", features.skip_already_processed, "Skips files matching the Processed filename patterns to avoid reprocessing."),
      checkboxField("Use filename as invoice number if not found", "features.number_fallback_to_filename", features.number_fallback_to_filename, "If the PDF text does not contain an invoice number, uses the original filename instead."),
      checkboxField("Add suffix if filenames would clash", "features.deduplicate_within_run", features.deduplicate_within_run, "If two files would get the same output name, appends _1, _2, etc."),
      checkboxField("Preview changes without saving", "features.dry_run", features.dry_run, "Shows what would happen but does not rename, copy, or move any files."),
      textareaField("Required invoice fields", "features.manual_review_for_missing", features.manual_review_for_missing, "If any listed field cannot be found, the file is renamed with the manual-review prefix for review. One per line."),
    ]));

    const parsers = cfg.parsers || {};
    const account = parsers.account || {};
    const number = parsers.number || {};
    const date = parsers.date || {};
    const currency = parsers.currency || {};
    const total = parsers.total || {};

    const details = date.details_block || {};

    form.appendChild(section("Invoice field extraction", [
      textareaField("Account search patterns", "parsers.account.patterns", account.patterns || [], "Regex patterns to find the account/customer name in the invoice text."),
      textareaField("Values that mean no account", "parsers.account.unknown_values", account.unknown_values || [], "If the found account matches any of these, treat it as missing."),
      textField("Default account name", "parsers.account.fallback", account.fallback, "Used when the account cannot be found."),
      textareaField("Invoice number search patterns", "parsers.number.patterns", number.patterns || [], "Regex patterns to find the invoice number in the invoice text."),
      checkboxField("Invoice number must contain digits", "parsers.number.require_digit", number.require_digit, "Reject matches that do not contain any numbers."),
      checkboxField("Allow filename as invoice number", "parsers.number.fallback_to_filename", number.fallback_to_filename, "Uses the original PDF filename as the invoice number when not found in text."),
      textField("Filename-only number pattern", "parsers.number.filename_pattern", number.filename_pattern, "When falling back to filename, only accept filenames matching this pattern as valid numbers."),
      textareaField("Date formats to recognise", "parsers.date.parse_formats", date.parse_formats || [], "Possible date formats found in the PDF text, e.g. \"%d %B %Y\"."),
      textField("Lines around Invoice date to search", "parsers.date.nearby_line_window", date.nearby_line_window, "How many lines above/below the Invoice date label to look for the date value."),
      checkboxField("Use details block to find dates", "parsers.date.details_block.enabled", details.enabled, "Enables the alternate date parser that looks at labelled sections below headers like Details."),
      textField("Details section header", "parsers.date.details_block.header", details.header, "The header text that marks the start of the details section, e.g. Details."),
      textField("Dotted separator line pattern", "parsers.date.details_block.dot_separator_regex", details.dot_separator_regex, "Pattern matching separator lines (e.g. dots) inside the details section."),
      textField("Label patterns inside details block", "parsers.date.details_block.label_regex", details.label_regex, "Patterns matching labels such as Invoice date in the details section."),
      textField("Maximum label length", "parsers.date.details_block.max_label_length", details.max_label_length, "Labels longer than this are ignored when matching inside the details block."),
      textField("Currency search pattern", "parsers.currency.primary_regex", currency.primary_regex, "Regex to find the invoice currency in the PDF text."),
      textareaField("Currency symbol to code mapping", "parsers.currency.symbol_map", currency.symbol_map || {}, "Maps symbols like HK$ to ISO codes like HKD."),
      textField("Total amount search pattern", "parsers.total.primary_regex", total.primary_regex, "Regex to find the total amount due in the PDF text."),
      textField("Fallback total amount pattern", "parsers.total.fallback_regex", total.fallback_regex, "Used if the primary total pattern finds nothing."),
      checkboxField("Use largest amount found", "parsers.total.pick_max", total.pick_max, "When multiple amounts match, use the highest one."),
    ]));

    const filename = cfg.filename || {};
    const placeholders = filename.placeholders || {};
    const accountPlaceholder = placeholders.account || {};
    const numberPlaceholder = placeholders.number || {};
    const datePlaceholder = placeholders.date || {};
    const totalPlaceholder = placeholders.total || {};
    const currencyPlaceholder = placeholders.currency || {};

    form.appendChild(section("Manual review and duplicates", [
      textField("Manual review prefix", "filename.manual_review_prefix", filename.manual_review_prefix, "Added to filenames when required fields are missing, e.g. 000_."),
      textareaField("Processed filename patterns", "filename.already_processed_patterns", filename.already_processed_patterns || [], "Filenames matching these are skipped on later runs."),
      textField("Duplicate filename suffix", "filename.collision_suffix", filename.collision_suffix, "Format for the suffix added when two files have the same target name, e.g. _{counter}."),
    ]));

    form.appendChild(section("Filename placeholder defaults", [
      checkboxField("Account: clean for filenames", "filename.placeholders.account.sanitize", accountPlaceholder.sanitize, "Remove characters that are invalid in filenames."),
      textField("Account: fallback value", "filename.placeholders.account.fallback", accountPlaceholder.fallback, "Used when account cannot be found."),
      checkboxField("Number: clean for filenames", "filename.placeholders.number.sanitize", numberPlaceholder.sanitize, "Remove characters that are invalid in filenames."),
      textField("Number: fallback value", "filename.placeholders.number.fallback", numberPlaceholder.fallback, "Used when invoice number cannot be found."),
      checkboxField("Date: clean for filenames", "filename.placeholders.date.sanitize", datePlaceholder.sanitize, "Remove characters that are invalid in filenames."),
      textField("Date: fallback value", "filename.placeholders.date.fallback", datePlaceholder.fallback, "Used when date cannot be found."),
      checkboxField("Total: clean for filenames", "filename.placeholders.total.sanitize", totalPlaceholder.sanitize, "Remove characters that are invalid in filenames."),
      textField("Total: fallback value", "filename.placeholders.total.fallback", totalPlaceholder.fallback, "Used when total cannot be found."),
      checkboxField("Currency: clean for filenames", "filename.placeholders.currency.sanitize", currencyPlaceholder.sanitize, "Remove characters that are invalid in filenames."),
      textField("Currency: fallback value", "filename.placeholders.currency.fallback", currencyPlaceholder.fallback, "Used when currency cannot be found."),
    ]));

    const archive = cfg.archive || {};
    form.appendChild(section("Archive settings", [
      selectField("Archive mode", "archive.mode", ["copy_original"], archive.mode, "How originals are archived. Currently only copy_original is supported."),
    ]));

    const rclone = cfg.rclone || {};
    form.appendChild(section("Google Drive sync", [
      checkboxField("Enable Google Drive sync", "rclone.enabled", rclone.enabled, "Turn on automatic sync with Google Drive via rclone."),
      textField("rclone remote name", "rclone.remote", rclone.remote, "The name of the rclone remote configured for Google Drive."),
      textField("Drive folder for raw invoices", "rclone.source_drive_folder", rclone.source_drive_folder, "Google Drive path to pull raw invoice PDFs from."),
      textField("Drive folder for processed invoices", "rclone.destination_drive_folder", rclone.destination_drive_folder, "Google Drive path to push renamed invoice PDFs to."),
      textField("Subfolder pattern for processed invoices", "rclone.destination_subfolder_template", rclone.destination_subfolder_template, "Organises pushed files into subfolders. Use {year}, {month}, {day}, {date}."),
      textField("Drive folder for archives (optional)", "rclone.archive_drive_folder", rclone.archive_drive_folder, "Google Drive path to push archived originals to. Leave blank to keep archives local only."),
    ]));

    const reports = cfg.reports || {};
    form.appendChild(section("CSV reports", [
      checkboxField("Enable CSV download", "reports.enabled", reports.enabled, "Allows downloading a CSV summary after previewing."),
      textField("CSV filename pattern", "reports.filename_template", reports.filename_template, "Name for the downloaded CSV. Use {timestamp} for the current time."),
    ]));

    const googleSheets = cfg.google_sheets || {};
    form.appendChild(section("Google Sheets reports", [
      checkboxField("Enable Google Sheets report", "google_sheets.enabled", googleSheets.enabled, "Appends processed invoice details to a Google Sheets spreadsheet."),
      textField("Spreadsheet URL", "google_sheets.spreadsheet_url", googleSheets.spreadsheet_url, "Full URL of the Google Sheets file to write to."),
      textField("Service account key path", "google_sheets.service_account_file", googleSheets.service_account_file, "Path to the JSON service account key. Leave blank to use default credentials."),
      textField("Tab name pattern", "google_sheets.tab_name_template", googleSheets.tab_name_template, "Name pattern for each monthly tab. Use %b for month abbreviation and %Y for year."),
      textField("Report date format", "google_sheets.date_format", googleSheets.date_format, "How dates are formatted in the report, e.g. %d/%m/%Y."),
      textField("Skip existing by", "google_sheets.skip_existing_by", googleSheets.skip_existing_by, "Field used to avoid duplicate rows. Currently only 'number' is supported."),
    ]));
  },

  collect() {
    const cfg = JSON.parse(JSON.stringify(this.originalConfig));
    const inputs = document.querySelectorAll("#config-form [data-key]");
    inputs.forEach((input) => {
      const key = input.dataset.key;
      const value = input.type === "checkbox" ? input.checked : this.parseValue(input.dataset.type, input.value);
      this.setPath(cfg, key, value);
    });
    return cfg;
  },

  parseValue(type, value) {
    if (type === "json") {
      try {
        return JSON.parse(value);
      } catch {
        return value;
      }
    }
    if (type === "number") {
      const n = Number(value);
      return Number.isNaN(n) ? value : n;
    }
    return value;
  },

  setPath(obj, path, value) {
    const parts = path.split(".");
    let current = obj;
    for (let i = 0; i < parts.length - 1; i++) {
      current = current[parts[i]];
    }
    current[parts[parts.length - 1]] = value;
  },

  async save() {
    const cfg = this.collect();
    try {
      const validation = await api.validateConfig(cfg);
      if (!validation.valid) {
        this.showError("Validation failed:\n" + validation.error);
        return;
      }
      await api.saveConfig(cfg);
      this.originalConfig = cfg;
      this.showSuccess("Config saved successfully.");
      this.showError("");
    } catch (err) {
      this.showError("Failed to save config: " + err.message);
    }
  },

  showError(message) {
    const el = document.getElementById("config-error");
    el.textContent = message;
    el.classList.toggle("hidden", !message);
  },

  showSuccess(message) {
    const el = document.getElementById("config-success");
    el.textContent = message;
    el.classList.toggle("hidden", !message);
  },
};

document.addEventListener("DOMContentLoaded", () => {
  const saveBtn = document.getElementById("config-save");
  const reloadBtn = document.getElementById("config-reload");
  if (saveBtn) saveBtn.addEventListener("click", () => configModule.save());
  if (reloadBtn) reloadBtn.addEventListener("click", () => configModule.load());
});

function section(title, fields) {
  const div = document.createElement("div");
  div.className = "form-section";
  const h3 = document.createElement("h3");
  h3.textContent = title;
  div.appendChild(h3);
  const row = document.createElement("div");
  row.className = "form-row";
  fields.forEach((f) => row.appendChild(f));
  div.appendChild(row);
  return div;
}

function textField(label, key, value, help) {
  return wrapField(label, `<input type="text" data-key="${key}" data-type="text" value="${escapeAttr(value ?? "")}">`, help);
}

function checkboxField(label, key, checked, help) {
  return wrapField(label, `<input type="checkbox" data-key="${key}" data-type="bool" ${checked ? "checked" : ""}>`, help);
}

function selectField(label, key, options, value, help) {
  const optionsHtml = options.map((opt) => `<option value="${escapeAttr(opt)}" ${opt === value ? "selected" : ""}>${escapeHtml(opt)}</option>`).join("");
  return wrapField(label, `<select data-key="${key}" data-type="text">${optionsHtml}</select>`, help);
}

function textareaField(label, key, value, help) {
  const json = Array.isArray(value) || typeof value === "object" ? JSON.stringify(value, null, 2) : value;
  return wrapField(label, `<textarea data-key="${key}" data-type="json">${escapeHtml(json ?? "")}</textarea>`, help);
}

function wrapField(label, inputHtml, help) {
  const helpMarker = help ? `<span class="field-help" data-tooltip="${escapeAttr(help)}">?</span>` : "";
  const div = document.createElement("div");
  div.className = "form-group";
  div.innerHTML = `<label>${escapeHtml(label)}${helpMarker}</label>${inputHtml}`;
  return div;
}
