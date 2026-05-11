import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tech-lab`;

export const useNotebooksStore = defineStore({
  id: "notebooks",
  state: () => ({
    tree: { folders: [], notebooks: [] },
    notebooks: {}, // id → full notebook (lazy)
    saveStatus: {}, // id → "idle" | "saving" | "saved" | "error"
    inFlight: {}, // notebookId → { executionId → execution }
    cellMeta: {}, // notebookId → { cellId → { durationMs, finishedAt, status } }
    status: {
      loadingTree: false,
      loadingNotebook: false,
      creating: false,
      updating: false,
      forking: false,
      error: null,
    },
  }),
  actions: {
    // ── tree ─────────────────────────────────────────────────────────────
    async loadTree() {
      this.status.loadingTree = true;
      this.status.error = null;
      try {
        this.tree = await fetchWrapper.get(`${baseUrl}/tree`);
        return this.tree;
      } catch (err) {
        this.status.error = err?.message || String(err);
        throw err;
      } finally {
        this.status.loadingTree = false;
      }
    },

    // ── folders ──────────────────────────────────────────────────────────
    async createFolder(payload) {
      this.status.creating = true;
      try {
        const folder = await fetchWrapper.post(`${baseUrl}/folders`, payload);
        await this.loadTree();
        return folder;
      } finally {
        this.status.creating = false;
      }
    },
    async updateFolder(id, patch) {
      this.status.updating = true;
      try {
        const folder = await fetchWrapper.patch(
          `${baseUrl}/folders/${id}`,
          patch,
        );
        await this.loadTree();
        return folder;
      } finally {
        this.status.updating = false;
      }
    },
    async deleteFolder(id) {
      await fetchWrapper.delete(`${baseUrl}/folders/${id}`);
      await this.loadTree();
    },

    // ── notebooks ────────────────────────────────────────────────────────
    async createNotebook(payload) {
      this.status.creating = true;
      try {
        const nb = await fetchWrapper.post(`${baseUrl}/notebooks`, payload);
        this.notebooks[nb.id] = nb;
        await this.loadTree();
        return nb;
      } finally {
        this.status.creating = false;
      }
    },
    async getNotebook(id) {
      this.status.loadingNotebook = true;
      try {
        const nb = await fetchWrapper.get(`${baseUrl}/notebooks/${id}`);
        this.notebooks[nb.id] = nb;
        return nb;
      } finally {
        this.status.loadingNotebook = false;
      }
    },
    async updateNotebook(id, patch) {
      this.saveStatus[id] = "saving";
      try {
        const nb = await fetchWrapper.patch(
          `${baseUrl}/notebooks/${id}`,
          patch,
        );
        this.notebooks[id] = nb;
        this.saveStatus[id] = "saved";
        return nb;
      } catch (err) {
        this.saveStatus[id] = "error";
        throw err;
      }
    },
    async deleteNotebook(id) {
      await fetchWrapper.delete(`${baseUrl}/notebooks/${id}`);
      delete this.notebooks[id];
      delete this.saveStatus[id];
      await this.loadTree();
    },
    async forkNotebook(id, visibility = "personal") {
      this.status.forking = true;
      try {
        const url =
          visibility === "personal"
            ? `${baseUrl}/notebooks/${id}/fork`
            : `${baseUrl}/notebooks/${id}/fork?visibility=${encodeURIComponent(visibility)}`;
        const nb = await fetchWrapper.post(url, {});
        this.notebooks[nb.id] = nb;
        await this.loadTree();
        return nb;
      } finally {
        this.status.forking = false;
      }
    },
    async clearOutputs(id) {
      const nb = await fetchWrapper.post(
        `${baseUrl}/notebooks/${id}/clear_outputs`,
        {},
      );
      this.notebooks[id] = nb;
      // Drop local timing too so the panel goes back to the empty state.
      if (this.cellMeta[id]) this.cellMeta[id] = {};
      return nb;
    },

    // ── import / export ──────────────────────────────────────────────────
    async exportNotebook(id) {
      // The export endpoint returns nbformat-shaped JSON; we hand it to the
      // browser as a Blob so the download keeps the .ipynb extension.
      const blob = await fetchWrapper.get(`${baseUrl}/notebooks/${id}/export`);
      return blob;
    },
    async importNotebook(file, folderId = null) {
      const url = folderId
        ? `${baseUrl}/notebooks/import?folder_id=${folderId}`
        : `${baseUrl}/notebooks/import`;
      const form = new FormData();
      form.append("file", file);
      const nb = await fetchWrapper.postFormData(url, form);
      this.notebooks[nb.id] = nb;
      await this.loadTree();
      return nb;
    },

    // ── execution ────────────────────────────────────────────────────────
    async executeCell(notebookId, cellId, source) {
      const exec = await fetchWrapper.post(
        `${baseUrl}/notebooks/${notebookId}/cells/execute`,
        { cell_id: cellId, source, timeout_seconds: 60 },
      );
      this._trackInFlight(notebookId, exec);
      this._poll(notebookId, exec.id);
      return exec;
    },
    async executeAll(notebookId) {
      const execs = await fetchWrapper.post(
        `${baseUrl}/notebooks/${notebookId}/cells/execute_all`,
        {},
      );
      for (const e of execs) {
        this._trackInFlight(notebookId, e);
        this._poll(notebookId, e.id);
      }
      return execs;
    },
    async getExecution(notebookId, executionId) {
      return fetchWrapper.get(
        `${baseUrl}/notebooks/${notebookId}/executions/${executionId}`,
      );
    },
    async interruptKernel(notebookId) {
      return fetchWrapper.post(
        `${baseUrl}/notebooks/${notebookId}/kernel/interrupt`,
        {},
      );
    },
    async shutdownKernel(notebookId) {
      return fetchWrapper.post(
        `${baseUrl}/notebooks/${notebookId}/kernel/shutdown`,
        {},
      );
    },

    // ── internals: poll until terminal, merge outputs ────────────────────
    _trackInFlight(notebookId, exec) {
      if (!this.inFlight[notebookId]) this.inFlight[notebookId] = {};
      this.inFlight[notebookId][exec.id] = exec;
    },
    _clearInFlight(notebookId, executionId) {
      if (!this.inFlight[notebookId]) return;
      delete this.inFlight[notebookId][executionId];
    },
    async _poll(notebookId, executionId) {
      const TERMINAL = new Set(["success", "error", "interrupted"]);
      // Light-weight loop with a 500ms cadence and a hard cap to avoid
      // pathological infinite polling on a stuck kernel.
      for (let i = 0; i < 600; i++) {
        await new Promise((r) => setTimeout(r, 500));
        let exec;
        try {
          exec = await this.getExecution(notebookId, executionId);
        } catch (err) {
          this._clearInFlight(notebookId, executionId);
          throw err;
        }
        if (this.inFlight[notebookId]) {
          this.inFlight[notebookId][executionId] = exec;
        }
        if (TERMINAL.has(exec.status)) {
          this._mergeOutputs(notebookId, exec);
          this._clearInFlight(notebookId, executionId);
          return exec;
        }
      }
      this._clearInFlight(notebookId, executionId);
    },
    _mergeOutputs(notebookId, exec) {
      const nb = this.notebooks[notebookId];
      if (!nb) return;
      const outputs = { ...(nb.cell_outputs || {}) };
      outputs[exec.cell_id] = exec.outputs || [];
      nb.cell_outputs = outputs;
      // Capture timing so the output panel can show a footer.
      // started_at / finished_at are ISO 8601 strings from the server.
      let durationMs = null;
      if (exec.started_at && exec.finished_at) {
        const start = Date.parse(exec.started_at);
        const end = Date.parse(exec.finished_at);
        if (!Number.isNaN(start) && !Number.isNaN(end)) {
          durationMs = Math.max(0, end - start);
        }
      }
      if (!this.cellMeta[notebookId]) this.cellMeta[notebookId] = {};
      this.cellMeta[notebookId][exec.cell_id] = {
        durationMs,
        finishedAt: exec.finished_at,
        status: exec.status,
      };
    },

    // ── helpers ──────────────────────────────────────────────────────────
    isOwner(notebookId, currentUserId) {
      const nb = this.notebooks[notebookId];
      if (!nb) {
        const summary = this.tree.notebooks.find((n) => n.id === notebookId);
        return summary ? summary.user_id === currentUserId : false;
      }
      return nb.user_id === currentUserId;
    },
    kernelBusy(notebookId) {
      const m = this.inFlight[notebookId];
      if (!m) return false;
      const TERMINAL = new Set(["success", "error", "interrupted"]);
      return Object.values(m).some((e) => !TERMINAL.has(e.status));
    },
  },
});
