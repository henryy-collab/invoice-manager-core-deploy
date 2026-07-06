const configModule = {
  originalConfig: null,
  selectedType: null,

  async load() {
    try {
      const data = await api.config();
      this.originalConfig = data.config;
      this.selectedType = data.config.default_document_type || Object.keys(data.config.document_types || {})[0];
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

    form.appendChild(this._renderGlobalSections(cfg));

    const typesPanel = document.createElement("div");
    typesPanel.className = "document-types-panel";
    typesPanel.appendChild(this._renderTypeSelector(cfg));
    typesPanel.appendChild(this._renderTypeEditor(cfg));
    form.appendChild(typesPanel);
  },

  _renderGlobalSections(cfg) {
    const container = document.createElement("div");
    container.className = "config-global-sections";

    container.appendChild(section("Folders", [
      textField("Root data folder", "source_folder", cfg.source_folder, "Base folder for invoice data. Other folders can be set relative to this."),
      textField("Raw invoices folder", "input_folder", cfg.input_folder, "Folder where unprocessed invoice PDFs are placed before running."),
      textField("Processed invoices folder", "output_folder", cfg.output_folder, "Folder where renamed invoice PDFs are saved after running."),
      textField("Archive folder", "archive_folder", cfg.archive_folder, "Where original PDF copies are stored when archiving is enabled."),
      textField("Log file", "log_file", cfg.log_file, "Where processing events are written."),
      textField("Timezone", "timezone", cfg.timezone, "Timezone used for timestamps in logs and reports."),
    ]));

    container.appendChild(section("Output filename defaults", [
      textField("Date format", "date_format", cfg.date_format, "Format for the {date} part of the output filename, e.g. %Y%m%d."),
    ]));

    const features = cfg.features || {};
    container.appendChild(section("Processing behaviour", [
      checkboxField("Keep copies of original PDFs", "features.archive", features.archive, "When enabled, copies each raw PDF to the archive folder before renaming."),
      checkboxField("Skip files that look already processed", "features.skip_already_processed", features.skip_already_processed, "Skips files matching the Processed filename patterns to avoid reprocessing."),
      checkboxField("Use filename as invoice number if not found", "features.number_fallback_to_filename", features.number_fallback_to_filename, "If the PDF text does not contain an invoice number, uses the original filename instead."),
      checkboxField("Add suffix if filenames would clash", "features.deduplicate_within_run", features.deduplicate_within_run, "If two files would get the same output name, appends _1, _2, etc."),
      checkboxField("Preview changes without saving", "features.dry_run", features.dry_run, "Shows what would happen but does not rename, copy, or move any files."),
    ]));

    const filename = cfg.filename || {};
    container.appendChild(section("Manual review and duplicates", [
      textField("Manual review prefix", "filename.manual_review_prefix", filename.manual_review_prefix, "Added to filenames when required fields are missing, e.g. 000_."),
      textareaField("Processed filename patterns", "filename.already_processed_patterns", filename.already_processed_patterns || [], "Filenames matching these are skipped on later runs."),
      textField("Duplicate filename suffix", "filename.collision_suffix", filename.collision_suffix, "Format for the suffix added when two files have the same target name, e.g. _{counter}."),
    ]));

    const archive = cfg.archive || {};
    container.appendChild(section("Archive settings", [
      selectField("Archive mode", "archive.mode", ["copy_original"], archive.mode, "How originals are archived. Currently only copy_original is supported."),
    ]));

    const rclone = cfg.rclone || {};
    container.appendChild(section("Google Drive sync", [
      checkboxField("Enable Google Drive sync", "rclone.enabled", rclone.enabled, "Turn on automatic sync with Google Drive via rclone."),
      textField("rclone remote name", "rclone.remote", rclone.remote, "The name of the rclone remote configured for Google Drive."),
      textField("Drive folder for raw invoices", "rclone.source_drive_folder", rclone.source_drive_folder, "Google Drive path to pull raw invoice PDFs from."),
      textField("Drive folder for processed invoices", "rclone.destination_drive_folder", rclone.destination_drive_folder, "Google Drive path to push renamed invoice PDFs to."),
      textField("Subfolder pattern for processed invoices", "rclone.destination_subfolder_template", rclone.destination_subfolder_template, "Organises pushed files into subfolders. Use {year}, {month}, {day}, {date}."),
      textField("Drive folder for archives (optional)", "rclone.archive_drive_folder", rclone.archive_drive_folder, "Google Drive path to push archived originals to. Leave blank to keep archives local only."),
    ]));

    const reports = cfg.reports || {};
    container.appendChild(section("CSV reports", [
      checkboxField("Enable CSV download", "reports.enabled", reports.enabled, "Allows downloading a CSV summary after previewing."),
      textField("CSV filename pattern", "reports.filename_template", reports.filename_template, "Name for the downloaded CSV. Use {timestamp} for the current time."),
    ]));

    const googleSheets = cfg.google_sheets || {};
    container.appendChild(section("Google Sheets reports", [
      checkboxField("Enable Google Sheets report", "google_sheets.enabled", googleSheets.enabled, "Appends processed invoice details to a Google Sheets spreadsheet."),
      textField("Spreadsheet URL", "google_sheets.spreadsheet_url", googleSheets.spreadsheet_url, "Full URL of the Google Sheets file to write to."),
      textField("Service account key path", "google_sheets.service_account_file", googleSheets.service_account_file, "Path to the JSON service account key. Leave blank to use default credentials."),
      textField("Tab name pattern", "google_sheets.tab_name_template", googleSheets.tab_name_template, "Name pattern for each monthly tab. Use %b for month abbreviation and %Y for year."),
      textField("Report date format", "google_sheets.date_format", googleSheets.date_format, "How dates are formatted in the report, e.g. %d/%m/%Y."),
      textField("Skip existing by", "google_sheets.skip_existing_by", googleSheets.skip_existing_by, "Field used to avoid duplicate rows. Currently only 'number' is supported."),
      textField("Raw sheet suffix", "google_sheets.raw_sheet_suffix", googleSheets.raw_sheet_suffix, "Suffix added to automatically created report tabs."),
      checkboxField("Protect raw sheets", "google_sheets.protect_raw_sheets", googleSheets.protect_raw_sheets, "Add warning-only protection to [Auto] sheets."),
    ]));

    return container;
  },

  _renderTypeSelector(cfg) {
    const panel = document.createElement("div");
    panel.className = "document-type-selector";

    const heading = document.createElement("h3");
    heading.textContent = "Document types";
    panel.appendChild(heading);

    const list = document.createElement("ul");
    list.className = "document-type-list";
    const types = cfg.document_types || {};
    Object.keys(types).forEach((typeName) => {
      const li = document.createElement("li");
      li.className = typeName === this.selectedType ? "active" : "";
      li.textContent = typeName + (typeName === cfg.default_document_type ? " (default)" : "");
      li.addEventListener("click", () => {
        this.selectedType = typeName;
        this.render(cfg);
      });
      list.appendChild(li);
    });
    panel.appendChild(list);

    const actions = document.createElement("div");
    actions.className = "document-type-actions";

    const addBtn = document.createElement("button");
    addBtn.className = "btn btn-secondary";
    addBtn.textContent = "Add type";
    addBtn.addEventListener("click", () => {
      const newName = prompt("New document type name (letters, numbers, underscores, dashes):");
      if (!newName || !/^[a-zA-Z0-9_-]+$/.test(newName)) return;
      if (cfg.document_types[newName]) {
        alert("A document type with that name already exists.");
        return;
      }
      cfg.document_types[newName] = this._emptyDocumentType();
      this.selectedType = newName;
      this.render(cfg);
    });
    actions.appendChild(addBtn);

    const removeBtn = document.createElement("button");
    removeBtn.className = "btn btn-danger";
    removeBtn.textContent = "Remove";
    removeBtn.addEventListener("click", () => {
      const typeName = this.selectedType;
      if (!typeName) return;
      if (typeName === cfg.default_document_type) {
        alert("Cannot remove the default document type. Set another type as default first.");
        return;
      }
      if (!confirm(`Remove document type "${typeName}"?`)) return;
      delete cfg.document_types[typeName];
      this.selectedType = cfg.default_document_type || Object.keys(cfg.document_types)[0];
      this.render(cfg);
    });
    actions.appendChild(removeBtn);

    const defaultBtn = document.createElement("button");
    defaultBtn.className = "btn btn-secondary";
    defaultBtn.textContent = "Set as default";
    defaultBtn.addEventListener("click", () => {
      if (!this.selectedType || !cfg.document_types[this.selectedType]) return;
      cfg.default_document_type = this.selectedType;
      this.render(cfg);
    });
    actions.appendChild(defaultBtn);

    panel.appendChild(actions);
    return panel;
  },

  _renderTypeEditor(cfg) {
    const typeName = this.selectedType;
    const typeConfig = (cfg.document_types || {})[typeName] || this._emptyDocumentType();

    const editor = document.createElement("div");
    editor.className = "document-type-editor";

    const title = document.createElement("h3");
    title.textContent = `Edit: ${typeName}`;
    editor.appendChild(title);

    editor.appendChild(section("Classifier", [
      textareaField("Classifier patterns", `document_types.${typeName}.classifier.patterns`, typeConfig.classifier?.patterns || [], "One regex pattern per line. Used to decide if a PDF belongs to this document type."),
    ]));

    editor.appendChild(section("Output filename", [
      textField("Filename pattern", `document_types.${typeName}.filename_template`, typeConfig.filename_template, "How renamed files are named. Use {account}, {number}, {date}, {total}, {currency}."),
    ]));

    const placeholders = typeConfig.placeholders || {};
    editor.appendChild(section("Filename placeholder defaults", [
      checkboxField("Account: clean for filenames", `document_types.${typeName}.placeholders.account.sanitize`, placeholders.account?.sanitize, "Remove characters that are invalid in filenames."),
      textField("Account: fallback value", `document_types.${typeName}.placeholders.account.fallback`, placeholders.account?.fallback, "Used when account cannot be found."),
      checkboxField("Number: clean for filenames", `document_types.${typeName}.placeholders.number.sanitize`, placeholders.number?.sanitize, "Remove characters that are invalid in filenames."),
      textField("Number: fallback value", `document_types.${typeName}.placeholders.number.fallback`, placeholders.number?.fallback, "Used when invoice number cannot be found."),
      checkboxField("Date: clean for filenames", `document_types.${typeName}.placeholders.date.sanitize`, placeholders.date?.sanitize, "Remove characters that are invalid in filenames."),
      textField("Date: fallback value", `document_types.${typeName}.placeholders.date.fallback`, placeholders.date?.fallback, "Used when date cannot be found."),
      checkboxField("Total: clean for filenames", `document_types.${typeName}.placeholders.total.sanitize`, placeholders.total?.sanitize, "Remove characters that are invalid in filenames."),
      textField("Total: fallback value", `document_types.${typeName}.placeholders.total.fallback`, placeholders.total?.fallback, "Used when total cannot be found."),
      checkboxField("Currency: clean for filenames", `document_types.${typeName}.placeholders.currency.sanitize`, placeholders.currency?.sanitize, "Remove characters that are invalid in filenames."),
      textField("Currency: fallback value", `document_types.${typeName}.placeholders.currency.fallback`, placeholders.currency?.fallback, "Used when currency cannot be found."),
    ]));

    editor.appendChild(this._renderFieldsSection(typeName, typeConfig.fields || {}));

    editor.appendChild(section("Manual review", [
      textareaField("Required fields", `document_types.${typeName}.manual_review_for_missing`, typeConfig.manual_review_for_missing || [], "If any listed field cannot be found, the file is renamed with the manual-review prefix for review. One per line."),
    ]));

    editor.appendChild(this._renderReportColumnsSection(typeName, typeConfig.report_columns || {}));

    return editor;
  },

  _renderFieldsSection(typeName, fields) {
    const div = document.createElement("div");
    div.className = "form-section";

    const h3 = document.createElement("h3");
    h3.textContent = "Field parsers";
    div.appendChild(h3);

    const row = document.createElement("div");
    row.className = "form-row document-type-fields";

    const knownFields = ["account", "number", "date", "currency", "total"];
    knownFields.forEach((fieldName) => {
      const fieldConfig = fields[fieldName] || { parser: fieldName };
      row.appendChild(this._renderFieldCard(typeName, fieldName, fieldConfig));
    });

    div.appendChild(row);
    return div;
  },

  _renderFieldCard(typeName, fieldName, fieldConfig) {
    const card = document.createElement("div");
    card.className = "field-card";

    const heading = document.createElement("h4");
    heading.textContent = fieldName;
    card.appendChild(heading);

    const parserOptions = ["account", "number", "date", "currency", "total", "custom"];
    const optionsHtml = parserOptions.map((opt) => {
      const selected = fieldConfig.parser === opt ? "selected" : "";
      return `<option value="${escapeAttr(opt)}" ${selected}>${escapeHtml(opt)}</option>`;
    }).join("");
    const selectHtml = `<select data-key="document_types.${typeName}.fields.${fieldName}.parser" data-type="text">${optionsHtml}</select>`;
    card.appendChild(wrapField("Parser", selectHtml, "Select the parser to use for this field."));

    const configText = document.createElement("textarea");
    configText.dataset.key = `document_types.${typeName}.fields.${fieldName}.__config`;
    configText.dataset.type = "json";
    const withoutParser = { ...fieldConfig };
    delete withoutParser.parser;
    configText.textContent = JSON.stringify(withoutParser, null, 2);
    card.appendChild(wrapField("Parser config (JSON)", configText.outerHTML, "Parser-specific configuration. See example config for the expected shape."));

    return card;
  },

  _renderReportColumnsSection(typeName, reportColumns) {
    const div = document.createElement("div");
    div.className = "form-section";

    const h3 = document.createElement("h3");
    h3.textContent = "Report columns";
    div.appendChild(h3);

    const row = document.createElement("div");
    row.className = "form-row";

    const fixedColumns = [
      "Client Ref.", "Platform", "Agreed Amount", "Invoice No.", "Amount",
      "Invoice Date", "Paid Date", "AM", "PM", "Informed AM & PM",
      "Top up date", "Topped Currency", "Topped amount", "Balance",
    ];
    const fieldOptions = ["", "account", "number", "date", "total", "currency"];

    fixedColumns.forEach((columnName) => {
      const currentField = Object.entries(reportColumns).find(([, col]) => col === columnName)?.[0] || "";
      const optionsHtml = fieldOptions.map((opt) => {
        const selected = opt === currentField ? "selected" : "";
        return `<option value="${escapeAttr(opt)}" ${selected}>${opt ? escapeHtml(opt) : "(none)"}</option>`;
      }).join("");
      const selectHtml = `<select data-key="document_types.${typeName}.report_columns.__column:${columnName}" data-type="text">${optionsHtml}</select>`;
      row.appendChild(wrapField(columnName, selectHtml, `Which field populates the "${columnName}" column in CSV and Google Sheets reports.`));
    });

    div.appendChild(row);
    return div;
  },

  _emptyDocumentType() {
    return {
      classifier: { patterns: [] },
      fields: {},
      filename_template: "{account}_{number}_Invoice_{date}.pdf",
      placeholders: {},
      manual_review_for_missing: ["account", "date"],
      report_columns: {},
    };
  },

  collect() {
    const cfg = JSON.parse(JSON.stringify(this.originalConfig));
    const inputs = document.querySelectorAll("#config-form [data-key]");
    inputs.forEach((input) => {
      const key = input.dataset.key;
      const value = input.type === "checkbox" ? input.checked : this.parseValue(input.dataset.type, input.value);

      if (key.includes(".__config")) {
        const basePath = key.replace(".__config", "");
        this._setFieldConfig(cfg, basePath, value);
      } else if (key.includes(".__column:")) {
        const [basePath, columnName] = key.split(".__column:");
        this._setReportColumn(cfg, basePath, columnName, value);
      } else {
        this.setPath(cfg, key, value);
      }
    });
    return cfg;
  },

  _setFieldConfig(cfg, path, jsonValue) {
    const parts = path.split(".");
    let current = cfg;
    for (let i = 0; i < parts.length - 1; i++) {
      current = current[parts[i]];
    }
    const fieldName = parts[parts.length - 1];
    const parent = current;
    const parser = parent[fieldName]?.parser || fieldName;
    let extra = {};
    try {
      extra = JSON.parse(jsonValue || "{}") || {};
    } catch {
      extra = {};
    }
    parent[fieldName] = { parser, ...extra };
  },

  _setReportColumn(cfg, path, columnName, value) {
    const parts = path.split(".");
    let current = cfg;
    for (let i = 0; i < parts.length - 1; i++) {
      current = current[parts[i]];
    }
    const reportColumns = current;
    if (!value) {
      Object.keys(reportColumns).forEach((field) => {
        if (reportColumns[field] === columnName) delete reportColumns[field];
      });
    } else {
      Object.keys(reportColumns).forEach((field) => {
        if (reportColumns[field] === columnName) delete reportColumns[field];
      });
      reportColumns[value] = columnName;
    }
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

function escapeHtml(str) {
  return String(str).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function escapeAttr(str) {
  return String(str).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
