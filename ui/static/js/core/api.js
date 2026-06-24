const api = {
  async get(path) {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`);
    return res.json();
  },

  async post(path, body = {}) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `POST ${path} failed: ${res.status}`);
    }
    return data;
  },

  files() {
    return this.get("/api/files");
  },

  fileSummary() {
    return this.get("/api/files/summary");
  },

  config() {
    return this.get("/api/config");
  },

  saveConfig(config) {
    return this.post("/api/config", { config });
  },

  validateConfig(config) {
    return this.post("/api/config/validate", { config });
  },

  preview() {
    return this.post("/api/parse/preview");
  },

  run(dryRun) {
    return this.post("/api/parse/run", { dry_run: dryRun });
  },

  updatePreview(sourceName, fields) {
    return this.post("/api/parse/update", { source_name: sourceName, fields });
  },

  syncStatus() {
    return this.get("/api/sync/status");
  },

  syncPull() {
    return this.post("/api/sync/incoming");
  },

  syncPush() {
    return this.post("/api/sync/outgoing");
  },

  syncArchive() {
    return this.post("/api/sync/archive");
  },

  syncClearInput() {
    return this.post("/api/sync/clear-input");
  },

  clearIncoming() {
    return this.post("/api/files/clear-incoming");
  },

  writeToReport() {
    return this.post("/api/sheets/write");
  },

  logs(limit = 200) {
    return this.get(`/api/logs?limit=${limit}`);
  },
};
