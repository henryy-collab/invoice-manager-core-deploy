const STORAGE_KEY = "invoiceManager.filesSections";

const filesModule = {
  _expanded: {
    incoming: true,
    outgoing: true,
  },

  async load() {
    try {
      this._loadExpandedState();
      this._applyExpandedState();
      await this._loadFolderInfo();

      const files = await api.files();
      const incoming = files.filter((f) => f.folder === "incoming");
      const outgoing = files.filter((f) => f.folder === "outgoing");

      this._renderIncoming(incoming);
      this._renderOutgoing(outgoing);
    } catch (err) {
      console.error("Failed to load files:", err);
    }
  },

  async _loadFolderInfo() {
    try {
      const data = await api.config();
      const cfg = data.config;
      document.getElementById("files-source").textContent = cfg.source_folder;
      document.getElementById("files-input-folder").textContent = cfg.input_folder || cfg.source_folder;
      document.getElementById("files-output-folder").textContent = cfg.output_folder || cfg.source_folder;
      document.getElementById("files-config-path").textContent = data.path;
    } catch (err) {
      console.error("Failed to load folder info:", err);
    }
  },

  _loadExpandedState() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (typeof parsed.incoming === "boolean") {
          this._expanded.incoming = parsed.incoming;
        }
        if (typeof parsed.outgoing === "boolean") {
          this._expanded.outgoing = parsed.outgoing;
        }
      }
    } catch (err) {
      console.error("Failed to load files section state:", err);
    }
  },

  _saveExpandedState() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this._expanded));
    } catch (err) {
      console.error("Failed to save files section state:", err);
    }
  },

  _applyExpandedState() {
    for (const section of document.querySelectorAll(".files-section")) {
      const key = section.dataset.section;
      const expanded = !!this._expanded[key];
      const wrapper = section.querySelector(".table-wrapper");
      const button = section.querySelector(".section-toggle");
      const chevron = section.querySelector(".chevron");

      if (wrapper) {
        wrapper.classList.toggle("collapsed", !expanded);
      }
      if (button) {
        button.setAttribute("aria-expanded", String(expanded));
      }
      if (chevron) {
        chevron.innerHTML = expanded ? "\u25be" : "\u25b8";
      }
    }
  },

  toggleSection(key) {
    this._expanded[key] = !this._expanded[key];
    this._saveExpandedState();
    this._applyExpandedState();
  },

  _renderIncoming(files) {
    const tbody = document.querySelector("#incoming-files-table tbody");
    tbody.innerHTML = "";

    if (files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No PDF files in the incoming folder.</td></tr>`;
      return;
    }

    for (const file of files) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(file.name)}</td>
        <td>${statusBadge(file.status)}</td>
        <td>${formatBytes(file.size)}</td>
        <td>${formatDate(file.modified)}</td>
        <td><a class="btn" href="/files/${encodeURIComponent(file.folder)}/${encodeURIComponent(file.name)}" target="_blank">Download</a></td>
      `;
      tbody.appendChild(tr);
    }
  },

  _renderOutgoing(files) {
    const tbody = document.querySelector("#outgoing-files-table tbody");
    tbody.innerHTML = "";

    if (files.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No PDF files in the outgoing folder.</td></tr>`;
      return;
    }

    for (const file of files) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${escapeHtml(file.name)}</td>
        <td>${formatBytes(file.size)}</td>
        <td>${formatDate(file.modified)}</td>
        <td><a class="btn" href="/files/${encodeURIComponent(file.folder)}/${encodeURIComponent(file.name)}" target="_blank">Download</a></td>
      `;
      tbody.appendChild(tr);
    }
  },
};

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("files-refresh");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => filesModule.load());
  }

  for (const button of document.querySelectorAll(".files-section .section-toggle")) {
    const section = button.closest(".files-section");
    if (!section) continue;
    const key = section.dataset.section;
    button.addEventListener("click", () => filesModule.toggleSection(key));
  }
});
