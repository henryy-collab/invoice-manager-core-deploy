const app = {
  currentTab: "process",

  init() {
    this.bindTabs();
    this.switchTab("process");
    this.startAutoRefresh();
  },

  bindTabs() {
    document.querySelectorAll(".nav-button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        this.switchTab(tab);
      });
    });
  },

  switchTab(tab) {
    this.currentTab = tab;
    document.querySelectorAll(".nav-button").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    document.querySelectorAll(".tab").forEach((section) => {
      section.classList.toggle("active", section.id === tab);
    });

    if (tab === "files") filesModule.load();
    if (tab === "process") workflowModule.load();
    if (tab === "config") configModule.load();
    if (tab === "logs") logsModule.load();
  },

  startAutoRefresh() {
    setInterval(() => {
      if (this.currentTab === "files") filesModule.load();
      if (this.currentTab === "logs" && logsModule.autoRefresh) logsModule.load();
    }, 5000);
  },
};

document.addEventListener("DOMContentLoaded", () => app.init());
