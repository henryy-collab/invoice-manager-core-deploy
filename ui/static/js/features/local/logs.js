const logsModule = {
  autoRefresh: true,

  init() {
    document.getElementById("logs-refresh").addEventListener("click", () => this.load());
    document.getElementById("logs-auto").addEventListener("change", (e) => {
      this.autoRefresh = e.target.checked;
    });
  },

  async load() {
    try {
      const logs = await api.logs(200);
      const tbody = document.querySelector("#logs-table tbody");
      tbody.innerHTML = "";

      if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No log entries yet.</td></tr>`;
        return;
      }

      for (const log of logs) {
        const tr = document.createElement("tr");
        const levelClass = log.level === "ERROR" ? "badge-manual_review" : log.level === "WARNING" ? "badge-unprocessed" : "badge-processed";
        tr.innerHTML = `
          <td>${log.timestamp || "-"}</td>
          <td><span class="badge ${levelClass}">${log.level}</span></td>
          <td>${escapeHtml(log.event)}</td>
          <td><pre>${log.extra ? escapeHtml(JSON.stringify(log.extra, null, 2)) : ""}</pre></td>
        `;
        tbody.appendChild(tr);
      }
    } catch (err) {
      console.error("Failed to load logs:", err);
    }
  },
};

document.addEventListener("DOMContentLoaded", () => logsModule.init());
