"use strict";

const FIELD_KEYS = ["account", "number", "date", "total", "currency"];
const STEPS = ["pull", "preview", "review", "rename", "report", "push", "clear"];

const workflowModule = {
  _state: {
    mode: "idle",
    pausedStep: null,
    completedSteps: new Set(),
    runningAction: null,
    previewData: null,
    pendingEdits: new Map(),
    syncStatus: null,
    lastResult: null,
  },

  async load() {
    await this._loadSyncStatus();
    this._renderState();
  },

  async processInvoices() {
    if (this._state.mode === "paused") {
      await this._resume();
      return;
    }

    if (this._state.mode === "end_to_end") return;

    const confirmed = await showModal(
      "Process Invoices",
      "This will run the full workflow: Pull, Preview, Rename, Report, Push and Clear Drive input. Continue?"
    );
    if (!confirmed) return;

    this._resetRunState();
    this._state.mode = "end_to_end";
    this._renderState();

    const rcloneReady = this._rcloneReady();
    if (!rcloneReady) {
      this._pause(
        "pull",
        "Google Drive sync is not configured. Go to Config, enable rclone, set the remote and source drive folder, then click Resume Processing.",
        true
      );
      return;
    }

    await this._runPull(true);
    if (this._state.mode !== "end_to_end") return;

    if (this._state.lastResult?.transferred === 0) {
      this._setOutput("No new invoices to process. Workflow finished.", false);
      this._resetRunState();
      return;
    }

    await this._runPreview(true);
    if (this._state.mode !== "end_to_end") return;

    if (this._state.previewData.manual_review_count > 0) {
      this._pause(
        "review",
        `${this._state.previewData.manual_review_count} file(s) need manual review. Edit the table cells, click Save Edits, then click Resume Processing.`,
        true
      );
      return;
    }

    await this._runRename(true);
    if (this._state.mode !== "end_to_end") return;

    await this._runReport(true);
    if (this._state.mode !== "end_to_end") return;

    await this._runPush(true);
    if (this._state.mode !== "end_to_end") return;

    await this._runClear(true);
    if (this._state.mode !== "end_to_end") return;

    this._setOutput("Workflow completed successfully.", false);
    this._resetRunState();
  },

  async _resume() {
    const step = this._state.pausedStep;
    if (!step) return;

    this._state.mode = "end_to_end";
    this._state.pausedStep = null;
    this._renderState();

    const resumeIndex = STEPS.indexOf(step);
    if (resumeIndex < 0) return;

    for (let i = resumeIndex; i < STEPS.length; i++) {
      if (this._state.mode !== "end_to_end") return;

      const nextStep = STEPS[i];
      if (nextStep === "pull") {
        await this._runPull(true);
        if (this._state.lastResult?.transferred === 0) {
          this._setOutput("No new invoices to process. Workflow finished.", false);
          this._resetRunState();
          return;
        }
      } else if (nextStep === "preview") {
        await this._runPreview(true);
      } else if (nextStep === "review") {
        await this._savePendingEdits();
        if (this._state.previewData?.manual_review_count > 0) {
          this._pause(
            "review",
            `${this._state.previewData.manual_review_count} file(s) still need manual review. Edit the table cells, click Save Edits, then click Resume Processing.`,
            true
          );
          return;
        }
        await this._runRename(true);
      } else if (nextStep === "rename") {
        await this._runRename(true);
      } else if (nextStep === "report") {
        await this._runReport(true);
      } else if (nextStep === "push") {
        await this._runPush(true);
      } else if (nextStep === "clear") {
        await this._runClear(true);
      }
    }

    if (this._state.mode === "end_to_end") {
      this._setOutput("Workflow completed successfully.", false);
      this._resetRunState();
    }
  },

  async _runPull(isPipeline) {
    await this._runStep("pull", isPipeline, async () => {
      const before = await this._countIncomingFiles();
      const result = await api.syncPull();
      if (!result.success) return result;
      const after = await this._countIncomingFiles();
      const transferred = Math.max(0, after - before);
      this._state.lastResult = { ...result, transferred };
      result.message = transferred === 0
        ? "Pull completed. No new files were downloaded."
        : `Pull completed. ${transferred} new file(s) downloaded.`;
      return result;
    });
  },

  async _runPreview(isPipeline) {
    await this._runStep("preview", isPipeline, async () => {
      const data = await api.preview();
      this._state.previewData = data;
      this._state.pendingEdits.clear();
      return data;
    });
  },

  async _runRename(isPipeline) {
    await this._savePendingEdits();

    const count = this._renameCount();
    if (count === 0) {
      this._setOutput("No files available to rename.", true);
      if (isPipeline) this._pause("rename", "No files available to rename.", true);
      return;
    }

    const confirmed = isPipeline
      ? await showModal("Confirm rename", `This will rename and archive ${count} PDF(s) locally. Continue?`)
      : true;
    if (!confirmed) {
      if (isPipeline) this._pause("rename", "Rename was cancelled. Click Resume Processing to continue.", false);
      return;
    }

    await this._runStep("rename", isPipeline, async () => {
      const result = await api.run(false);
      if (!result.success) return result;
      this._state.previewData = null;
      this._state.pendingEdits.clear();
      filesModule.load();
      logsModule.load();
      return result;
    });
  },

  async _runReport(isPipeline) {
    await this._runStep("report", isPipeline, async () => {
      const result = await api.writeToReport();
      if (!result.success && !result.skipped) {
        return result;
      }
      if (result.skipped) {
        return { success: false, error: result.message || "Google Sheets reporting is not configured." };
      }
      return result;
    });
  },

  async _runPush(isPipeline) {
    const count = await this._countOutgoingFiles();
    if (count === 0) {
      this._setOutput("No files in outgoing folder to push.", true);
      if (isPipeline) this._pause("push", "No files in outgoing folder to push.", true);
      return;
    }

    const confirmed = isPipeline
      ? await showModal("Confirm push", `This will upload ${count} file(s) from the outgoing folder to Google Drive. Continue?`)
      : await showModal("Confirm push", "This will upload renamed PDFs to Google Drive. Continue?");
    if (!confirmed) {
      if (isPipeline) this._pause("push", "Push was cancelled. Click Resume Processing to continue.", false);
      return;
    }

    await this._runStep("push", isPipeline, async () => {
      const result = await api.syncPush();
      return result;
    });
  },

  async _runClear(isPipeline) {
    if (!this._state.syncStatus?.can_clear_remote_input) {
      this._setOutput("Clear Drive Input is not available. No successful run state was recorded.", true);
      if (isPipeline) this._pause("clear", "Clear Drive Input is not available. No successful run state was recorded.", true);
      return;
    }

    const confirmed = isPipeline
      ? await showModal("Confirm clear input", "This will delete the original raw files from the Google Drive input folder. Continue?")
      : await showModal("Confirm clear input", "This will delete processed files from the Google Drive input folder. Continue?");
    if (!confirmed) {
      if (isPipeline) this._pause("clear", "Clear Drive Input was cancelled. Click Resume Processing to continue.", false);
      return;
    }

    await this._runStep("clear", isPipeline, async () => {
      const result = await api.syncClearInput();
      return result;
    });
  },

  async _runStep(step, isPipeline, action) {
    this._state.runningAction = step;
    this._renderState();
    this._setOutput(isPipeline ? `Step ${STEPS.indexOf(step) + 1}/${STEPS.length}: ${this._stepLabel(step)}...` : `${this._stepLabel(step)}...`, false);

    try {
      const result = await action();
      if (result && result.success === false && !result.skipped) {
        throw new Error(result.error || result.stderr || result.message || "Unknown error");
      }

      this._setOutput(result?.message || `${this._stepLabel(step)} completed.`, false);

      if (this._state.mode === "paused") return;

      this._state.completedSteps.add(step);
      filesModule.load();
      if (step !== "pull") logsModule.load();
      await this._loadSyncStatus();
    } catch (err) {
      this._setOutput(`${isPipeline ? "Workflow" : this._stepLabel(step)} failed: ${err.message}`, true);
      if (isPipeline) {
        this._pause(step, `${this._stepLabel(step)} failed: ${err.message}. Fix the issue, then click Resume Processing.`, true);
      }
    } finally {
      this._state.runningAction = null;
      this._renderState();
    }
  },

  _stepLabel(step) {
    const labels = {
      pull: "Pull from Google Drive",
      preview: "Preview fields",
      review: "Review and edit",
      rename: "Rename files",
      report: "Write info to Report",
      push: "Push to Google Drive",
      clear: "Clear Drive input folder",
    };
    return labels[step] || step;
  },

  _pause(step, message, isError) {
    this._state.mode = "paused";
    this._state.pausedStep = step;
    this._setOutput(message, isError);
    this._renderState();
  },

  _resetRunState() {
    this._state.mode = "idle";
    this._state.pausedStep = null;
    this._state.completedSteps.clear();
    this._state.runningAction = null;
    this._state.previewData = null;
    this._state.pendingEdits.clear();
    this._state.lastResult = null;
    this._renderState();
  },

  async _startOver() {
    const modal = document.getElementById("start-over-modal");
    const incomingCheckbox = document.getElementById("start-over-clear-incoming");
    const outgoingCheckbox = document.getElementById("start-over-clear-outgoing");
    const confirmBtn = document.getElementById("start-over-confirm");
    const cancelBtn = document.getElementById("start-over-cancel");

    incomingCheckbox.checked = false;
    outgoingCheckbox.checked = false;
    modal.classList.remove("hidden");

    const result = await new Promise((resolve) => {
      const onConfirm = () => resolve({ confirmed: true, clearIncoming: incomingCheckbox.checked, clearOutgoing: outgoingCheckbox.checked });
      const onCancel = () => resolve({ confirmed: false });
      confirmBtn.onclick = onConfirm;
      cancelBtn.onclick = onCancel;
    });

    modal.classList.add("hidden");
    if (!result.confirmed) return;

    if (result.clearIncoming) {
      this._setOutput("Clearing local incoming folder...", false);
      try {
        const clearResult = await api.clearIncoming();
        if (!clearResult.success) throw new Error(clearResult.error || "Clear incoming failed");
        this._setOutput(clearResult.message, false);
        filesModule.load();
      } catch (err) {
        this._setOutput(`Could not clear incoming folder: ${err.message}`, true);
        return;
      }
    }

    if (result.clearOutgoing) {
      this._setOutput("Clearing local outgoing folder...", false);
      try {
        const clearResult = await api.clearOutgoing();
        if (!clearResult.success) throw new Error(clearResult.error || "Clear outgoing failed");
        this._setOutput(clearResult.message, false);
        filesModule.load();
      } catch (err) {
        this._setOutput(`Could not clear outgoing folder: ${err.message}`, true);
        return;
      }
    }

    this._resetRunState();
    this._setOutput("Workflow reset. Ready to process.", false);
  },

  _rcloneReady() {
    const s = this._state.syncStatus;
    return !!s?.enabled && !!s?.rclone_available && !!s?.source_drive_folder;
  },

  _renameCount() {
    if (!this._state.previewData) return 0;
    return this._state.previewData.results.length;
  },

  async _countIncomingFiles() {
    try {
      const files = await api.files();
      return files.filter((f) => f.folder === "incoming").length;
    } catch (err) {
      return 0;
    }
  },

  async _countOutgoingFiles() {
    try {
      const files = await api.files();
      return files.filter((f) => f.folder === "outgoing").length;
    } catch (err) {
      return 0;
    }
  },

  async _loadSyncStatus() {
    try {
      const status = await api.syncStatus();
      this._state.syncStatus = status;
      this._renderSyncStatus(status);
    } catch (err) {
      this._renderSyncStatus(null);
    }
  },

  _renderSyncStatus(status) {
    const container = document.getElementById("workflow-status");
    if (!status) {
      container.innerHTML = `<span class="workflow-status-item">Sync status unavailable</span>`;
      return;
    }

    const enabledBadge = status.enabled
      ? `<span class="badge badge-processed">Enabled</span>`
      : `<span class="badge badge-unprocessed">Disabled</span>`;
    const rcloneBadge = status.rclone_available
      ? `<span class="badge badge-processed">rclone available</span>`
      : `<span class="badge badge-manual_review">rclone not found</span>`;

    const source = status.source_drive_folder
      ? `${status.remote}:${status.source_drive_folder} → input`
      : "Source not configured";
    const destination = status.destination_drive_folder
      ? `output → ${status.remote}:${status.destination_drive_folder}`
      : "Destination not configured";
    const archive = status.archive_drive_folder
      ? `archive → ${status.remote}:${status.archive_drive_folder}`
      : "Archive not configured";
    const clearReady = status.can_clear_remote_input
      ? `<span class="badge badge-processed">clear ready</span>`
      : "";

    container.innerHTML = `
      ${enabledBadge}
      ${rcloneBadge}
      <span class="workflow-status-item">${escapeHtml(source)}</span>
      <span class="workflow-status-item">${escapeHtml(destination)}</span>
      <span class="workflow-status-item">${escapeHtml(archive)}</span>
      ${clearReady}
    `;
  },

  async saveEdits() {
    await this._savePendingEdits();
  },

  async _savePendingEdits() {
    if (!this._state.previewData || this._state.pendingEdits.size === 0) return;

    for (const [sourceName, fields] of this._state.pendingEdits) {
      const response = await api.updatePreview(sourceName, fields);
      this._state.previewData = response;
    }
    this._state.pendingEdits.clear();
    this._render(this._state.previewData);
    this._setOutput("Edits saved.", false);
    this._renderState();
  },

  _markPending(sourceName, field, value) {
    if (!this._state.pendingEdits.has(sourceName)) {
      this._state.pendingEdits.set(sourceName, {});
    }
    this._state.pendingEdits.get(sourceName)[field] = value;
    const row = document.querySelector(`tr[data-source-name="${escapeAttr(sourceName)}"]`);
    if (row) {
      row.classList.add("pending-edit");
    }
    this._renderState();
  },

  _render(data) {
    const summary = document.getElementById("process-summary");
    summary.innerHTML = `
      <div class="summary-item">Processed: ${data.processed_count}</div>
      <div class="summary-item">Manual review: ${data.manual_review_count}</div>
      <div class="summary-item">Skipped: ${data.skipped_count}</div>
      <div class="summary-item">Failed: ${data.failed_count}</div>
    `;

    const reviewDesc = document.getElementById("review-step-desc");
    if (reviewDesc) {
      reviewDesc.textContent = data.results.length
        ? `Review ${data.results.length} file(s) below and edit cells if needed.`
        : "No files to review.";
    }

    const tbody = document.querySelector("#process-table tbody");
    tbody.innerHTML = "";

    if (data.results.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" class="empty-state">No files to process.</td></tr>`;
      return;
    }

    for (const r of data.results) {
      const f = r.fields;
      const status = r.needs_manual_review ? "manual_review" : "processed";
      const tr = document.createElement("tr");
      tr.dataset.sourceName = r.source_name;
      tr.className = this._state.pendingEdits.has(r.source_name) ? "pending-edit" : "";
      tr.innerHTML = `
        <td>${escapeHtml(r.source_name)}${r.number_fallback_used ? " *" : ""}</td>
        ${this._editableCell(r.source_name, "account", f.account)}
        ${this._editableCell(r.source_name, "number", f.number)}
        ${this._editableCell(r.source_name, "date", f.date)}
        ${this._editableCell(r.source_name, "total", f.total)}
        ${this._editableCell(r.source_name, "currency", f.currency)}
        <td>${escapeHtml(r.target_name)}</td>
        <td>${statusBadge(status)}${r.missing_required.length ? " (" + r.missing_required.join(", ") + ")" : ""}</td>
      `;
      tbody.appendChild(tr);
    }
  },

  _editableCell(sourceName, field, value) {
    return `
      <td class="editable-cell">
        <input type="text" class="inline-edit" value="${escapeAttr(value || "")}"
          data-source-name="${escapeAttr(sourceName)}" data-field="${escapeAttr(field)}"
          placeholder="-">
      </td>
    `;
  },

  _setStepVisuals() {
    const s = this._state;
    document.querySelectorAll(".workflow-step").forEach((el) => {
      const step = el.dataset.step;
      el.classList.remove("active", "done", "paused", "skipped", "running", "expanded");

      if (s.runningAction === step) {
        el.classList.add("running", "expanded");
      } else if (s.pausedStep === step) {
        el.classList.add("paused", "expanded");
      } else if (s.completedSteps.has(step)) {
        el.classList.add("done");
      }
    });
  },

  _computeState() {
    const s = this._state;
    const syncReady = s.syncStatus?.enabled && s.syncStatus?.rclone_available;
    const hasPreview = !!s.previewData;
    const hasFiles = hasPreview && s.previewData.results.length > 0;
    const hasPendingEdits = s.pendingEdits.size > 0;
    const isIdle = s.mode === "idle";
    const isPaused = s.mode === "paused";
    const isRunning = s.mode === "end_to_end";
    const running = s.runningAction;

    return {
      processButton: {
        label: isPaused ? "Resume Processing" : "Process Invoices",
        disabled: isRunning || !!running,
      },
      startOverButton: {
        hidden: isIdle && !running,
      },
      saveEdits: { disabled: !hasPendingEdits || !!running, running: false },
      download: { disabled: !hasFiles || !!running, running: false },
      advanced: {
        pull: { disabled: !syncReady || isRunning || !!running, running: running === "pull" },
        preview: { disabled: isRunning || !!running, running: running === "preview" },
        rename: { disabled: !hasFiles || isRunning || !!running, running: running === "rename" },
        writeReport: { disabled: !(s.completedSteps.has("rename") || s.completedSteps.has("push")) || isRunning || !!running, running: running === "report" },
        push: { disabled: !syncReady || isRunning || !!running, running: running === "push" },
        pushArchive: { disabled: !syncReady || !s.syncStatus?.archive_drive_folder || isRunning || !!running, running: running === "pushArchive" },
        clearInput: { disabled: !syncReady || !s.syncStatus?.can_clear_remote_input || isRunning || !!running, running: running === "clear" },
      },
      currentStep: s.pausedStep || s.runningAction,
      progress: this._computeProgress(),
    };
  },

  _computeProgress() {
    const s = this._state;
    if (s.mode === "idle" && s.completedSteps.size === 0) return 0;
    const currentIndex = s.pausedStep ? STEPS.indexOf(s.pausedStep) : (s.runningAction ? STEPS.indexOf(s.runningAction) : -1);
    let completed = s.completedSteps.size;
    if (currentIndex >= 0) {
      completed += 0.5;
    }
    return Math.min(100, Math.round((completed / STEPS.length) * 100));
  },

  _renderState() {
    const computed = this._computeState();

    const processBtn = document.getElementById("workflow-process");
    if (processBtn) {
      processBtn.textContent = computed.processButton.label;
      processBtn.disabled = computed.processButton.disabled;
      processBtn.classList.toggle("btn-primary", computed.processButton.label === "Process Invoices");
      processBtn.classList.toggle("btn-secondary", computed.processButton.label === "Resume Processing");
    }

    const startOverBtn = document.getElementById("workflow-start-over");
    if (startOverBtn) {
      startOverBtn.classList.toggle("hidden", computed.startOverButton.hidden);
    }

    this._setButton("workflow-save-edits", computed.saveEdits);
    this._setButton("workflow-download", computed.download);

    const adv = computed.advanced;
    this._setButton("workflow-pull", adv.pull);
    this._setButton("workflow-preview", adv.preview);
    this._setButton("workflow-rename", adv.rename);
    this._setButton("workflow-write-report", adv.writeReport);
    this._setButton("workflow-push", adv.push);
    this._setButton("workflow-push-archive", adv.pushArchive);
    this._setButton("workflow-clear-input", adv.clearInput);

    this._setStepVisuals();
    document.getElementById("workflow-progress-fill").style.width = `${computed.progress}%`;

    if (this._state.previewData) {
      this._render(this._state.previewData);
    } else {
      document.getElementById("process-summary").innerHTML = "";
      const tbody = document.querySelector("#process-table tbody");
      if (this._state.completedSteps.has("rename") || this._state.completedSteps.has("push") || this._state.completedSteps.has("clear")) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Files processed. Use the Files tab to see results.</td></tr>`;
      } else {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-state">Click Process Invoices or Preview to see planned renames.</td></tr>`;
      }
    }
  },

  _setButton(id, meta) {
    const el = document.getElementById(id);
    if (!el) return;
    el.disabled = meta.disabled;
    el.classList.toggle("btn-loading", meta.running);
  },

  _setOutput(message, isError) {
    const el = document.getElementById("workflow-output");
    if (!message) {
      el.classList.add("hidden");
      return;
    }
    el.textContent = message;
    el.className = isError ? "alert alert-error" : "alert alert-success";
    el.classList.remove("hidden");
  },

  async downloadCsv() {
    await this._runStep("download", false, async () => {
      const response = await fetch("/api/reports/export", { method: "POST" });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.error || `Export failed: ${response.status}`);
      }

      const blob = await response.blob();
      const filename = response.headers.get("Content-Disposition")?.match(/filename="?([^"]+)"?/)?.[1] || "parsed_fields.csv";
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      return { success: true };
    });
  },

  async pull() {
    await this._runPull(false);
  },

  async preview() {
    await this._runPreview(false);
  },

  async renameFiles() {
    await this._runRename(false);
  },

  async writeToReport() {
    await this._runReport(false);
  },

  async push() {
    await this._runPush(false);
  },

  async pushArchive() {
    await this._runStep("pushArchive", false, () => api.syncArchive());
  },

  async clearInput() {
    await this._runClear(false);
  },
};

function _bindButton(id, handler) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`Workflow button not found: ${id}`);
    return;
  }
  el.addEventListener("click", handler);
}

document.addEventListener("DOMContentLoaded", () => {
  _bindButton("workflow-process", () => workflowModule.processInvoices());
  _bindButton("workflow-start-over", () => workflowModule._startOver());
  _bindButton("workflow-pull", () => workflowModule.pull());
  _bindButton("workflow-preview", () => workflowModule.preview());
  _bindButton("workflow-save-edits", () => workflowModule.saveEdits());
  _bindButton("workflow-rename", () => workflowModule.renameFiles());
  _bindButton("workflow-write-report", () => workflowModule.writeToReport());
  _bindButton("workflow-push", () => workflowModule.push());
  _bindButton("workflow-push-archive", () => workflowModule.pushArchive());
  _bindButton("workflow-clear-input", () => workflowModule.clearInput());
  _bindButton("workflow-download", () => workflowModule.downloadCsv());

  document.querySelector("#process-table tbody").addEventListener("change", (e) => {
    const input = e.target.closest(".inline-edit");
    if (!input) return;
    const sourceName = input.dataset.sourceName;
    const field = input.dataset.field;
    const value = input.value.trim() || null;
    workflowModule._markPending(sourceName, field, value);
  });

  const advancedToggle = document.getElementById("workflow-advanced-toggle");
  const advancedBody = document.getElementById("workflow-advanced-body");
  if (advancedToggle && advancedBody) {
    advancedToggle.addEventListener("click", () => {
      const expanded = advancedBody.classList.toggle("collapsed");
      advancedToggle.setAttribute("aria-expanded", String(!expanded));
    });
    advancedToggle.setAttribute("aria-expanded", "false");
  }

  workflowModule.load();
});
