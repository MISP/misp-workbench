<script setup>
import {
  ref,
  shallowRef,
  watch,
  computed,
  onMounted,
  onBeforeUnmount,
} from "vue";
import { storeToRefs } from "pinia";
import { useNotebooksStore, useToastsStore } from "@/stores";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import {
  faCodeBranch,
  faPlay,
  faForwardStep,
  faBook,
  faDownload,
  faCode,
  faColumns,
  faTableList,
  faBroom,
  faPlus,
  faFileLines,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import KernelStatusPill from "./KernelStatusPill.vue";
import MwctipyReferenceModal from "./MwctipyReferenceModal.vue";
import OutputPanel from "./OutputPanel.vue";
import { parseCells, findCellAtLine, uuid } from "./cellDelimiterParser";

const props = defineProps({
  notebookId: { type: Number, default: null },
  currentUserId: { type: Number, default: null },
});

const emit = defineEmits(["select-notebook"]);

const notebooksStore = useNotebooksStore();
const toastsStore = useToastsStore();
const {
  saveStatus,
  notebooks: storeNotebooks,
  inFlight,
  cellMeta,
} = storeToRefs(notebooksStore);

const editorRef = shallowRef(null);
const monaco = shallowRef(null);

// id → ITextModel (kept outside reactive state to preserve Monaco identity).
const models = new Map();

const currentNotebook = ref(null);
const loading = ref(false);

// ── View-mode toggle (code | split | output), persisted to localStorage ──

const VIEW_MODE_KEY = "misp-workbench:notebooks:viewMode";
const viewMode = ref(localStorage.getItem(VIEW_MODE_KEY) || "split");
watch(viewMode, (m) => {
  try {
    localStorage.setItem(VIEW_MODE_KEY, m);
  } catch {
    /* quota / disabled — ignore */
  }
});

const showEditor = computed(() => viewMode.value !== "output");
const showOutputs = computed(() => viewMode.value !== "code");

// Reactive snapshot of the current notebook from the store (so output panel
// re-renders whenever cell_outputs are merged after a poll completes).
const liveNotebook = computed(() => {
  if (!currentNotebook.value) return null;
  return (
    storeNotebooks.value[currentNotebook.value.id] || currentNotebook.value
  );
});

const liveCellOutputs = computed(() => liveNotebook.value?.cell_outputs || {});
const liveCellMeta = computed(() => {
  if (!currentNotebook.value) return {};
  return cellMeta.value[currentNotebook.value.id] || {};
});

// ── Ownership / read-only ───────────────────────────────────────────────

const isLibrary = computed(
  () => currentNotebook.value?.visibility === "library",
);

const isOwner = computed(() => {
  if (!currentNotebook.value || props.currentUserId == null) return false;
  if (isLibrary.value) return false; // library is read-only regardless of seed owner
  return currentNotebook.value.user_id === props.currentUserId;
});

const readOnly = computed(
  () => currentNotebook.value != null && !isOwner.value,
);

const currentSaveStatus = computed(() => {
  if (currentNotebook.value == null) return "idle";
  return saveStatus.value[currentNotebook.value.id] || "idle";
});

const TERMINAL_STATUSES = new Set(["success", "error", "interrupted"]);
const kernelBusy = computed(() => {
  if (currentNotebook.value == null) return false;
  const m = inFlight.value[currentNotebook.value.id];
  if (!m) return false;
  return Object.values(m).some((e) => !TERMINAL_STATUSES.has(e.status));
});

const kernelStatus = computed(() => (kernelBusy.value ? "busy" : "idle"));

const monacoOptions = computed(() => ({
  fontSize: 13,
  minimap: { enabled: true },
  scrollBeyondLastLine: true,
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: "on",
  readOnly: readOnly.value,
}));

// ── Theme ───────────────────────────────────────────────────────────────

function detectMonacoTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "vs-dark"
    : "vs";
}
const monacoTheme = ref(detectMonacoTheme());
let themeObserver = null;

onMounted(() => {
  themeObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.attributeName === "data-bs-theme")) {
      monacoTheme.value = detectMonacoTheme();
    }
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-bs-theme"],
  });
});

onBeforeUnmount(() => {
  themeObserver?.disconnect();
  themeObserver = null;
  for (const m of models.values()) {
    try {
      m.dispose();
    } catch {
      /* noop */
    }
  }
  models.clear();
});

// ── Monaco model swap ───────────────────────────────────────────────────

// Track every model edit so liveSource() gets re-evaluated.
const _editTick = ref(0);

function onEditorMount(editor, monacoInstance) {
  editorRef.value = editor;
  monaco.value = monacoInstance;
  // Shift+Enter — Jupyter convention: run the current cell and advance the
  // cursor to the start of the next cell.
  editor.addCommand(
    monacoInstance.KeyMod.Shift | monacoInstance.KeyCode.Enter,
    () => runAndAdvance(),
  );
  if (currentNotebook.value) swapModel(currentNotebook.value);
}

function ensureModelFor(notebook) {
  if (!monaco.value) return null;
  let model = models.get(notebook.id);
  if (!model) {
    model = monaco.value.editor.createModel(notebook.source || "", "python");
    models.set(notebook.id, model);
    model.onDidChangeContent(() => onModelChange(notebook.id));
  } else if (notebook.source != null && model.getValue() !== notebook.source) {
    model.setValue(notebook.source);
  }
  return model;
}

function swapModel(notebook) {
  if (!editorRef.value || !monaco.value) return;
  const model = ensureModelFor(notebook);
  if (model) editorRef.value.setModel(model);
  _editTick.value++;
}

// ── Auto-save (1s debounce) ─────────────────────────────────────────────

const _saveTimers = new Map();
function onModelChange(notebookId) {
  if (currentNotebook.value?.id !== notebookId) return;
  _editTick.value++;
  if (readOnly.value) return;
  const existing = _saveTimers.get(notebookId);
  if (existing) clearTimeout(existing);
  const t = setTimeout(() => flushSave(notebookId), 1000);
  _saveTimers.set(notebookId, t);
  notebooksStore.saveStatus[notebookId] = "saving";
}

async function flushSave(notebookId) {
  _saveTimers.delete(notebookId);
  const model = models.get(notebookId);
  if (!model) return;
  const source = model.getValue();
  try {
    await notebooksStore.updateNotebook(notebookId, { source });
  } catch (err) {
    toastsStore.push(`Auto-save failed: ${err?.message || err}`, "danger");
  }
}

// ── React to notebook prop changes ──────────────────────────────────────

watch(
  () => props.notebookId,
  async (newId) => {
    if (newId == null) {
      currentNotebook.value = null;
      return;
    }
    loading.value = true;
    try {
      const nb = await notebooksStore.getNotebook(newId);
      currentNotebook.value = nb;
      swapModel(nb);
    } catch (err) {
      toastsStore.push(
        `Failed to load notebook: ${err?.message || err}`,
        "danger",
      );
      currentNotebook.value = null;
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

// Source string the OutputPanel reads. The Monaco model is not reactive, so
// we subscribe to ``_editTick`` (bumped on every onDidChangeContent) and
// call ``model.getValue()`` inline — wrapping it in another computed would
// hide the read behind a cached layer and stale-render markdown until the
// next notebook switch.
const trackedSource = computed(() => {
  void _editTick.value;
  const model = models.get(currentNotebook.value?.id);
  if (model) return model.getValue();
  return liveNotebook.value?.source || "";
});

// ── Run cell / Run all / Interrupt / Restart ────────────────────────────

function cellAtCursor() {
  if (!editorRef.value) return null;
  const model = models.get(currentNotebook.value?.id);
  if (!model) return null;
  const pos = editorRef.value.getPosition();
  if (!pos) return null;
  const cells = parseCells(model.getValue());
  return findCellAtLine(cells, pos.lineNumber);
}

async function runCell() {
  if (!currentNotebook.value || isLibrary.value) return;
  const cell = cellAtCursor();
  if (!cell) {
    toastsStore.push("Place the cursor inside a code cell first.", "warning");
    return;
  }
  if (cell.type !== "code") {
    toastsStore.push("Markdown cells aren't executed.", "info");
    return;
  }
  await flushSave(currentNotebook.value.id);
  try {
    await notebooksStore.executeCell(
      currentNotebook.value.id,
      cell.cellId,
      cell.source,
    );
  } catch (err) {
    toastsStore.push(`Run failed: ${err?.message || err}`, "danger");
  }
}

// Shift+Enter handler — run current cell, then move the cursor to the start
// of the next cell's body. Falls back to staying put if no next cell.
async function runAndAdvance() {
  if (!currentNotebook.value || isLibrary.value || !editorRef.value) return;
  const model = models.get(currentNotebook.value.id);
  if (!model) return;
  const cells = parseCells(model.getValue());
  const pos = editorRef.value.getPosition();
  if (!pos) return;
  const idx = cells.findIndex(
    (c) =>
      (pos.lineNumber >= c.sourceStartLine &&
        pos.lineNumber <= c.sourceEndLine) ||
      pos.lineNumber === c.delimiterLine,
  );
  if (idx === -1) return;
  const cell = cells[idx];
  if (cell.type === "code") {
    await flushSave(currentNotebook.value.id);
    try {
      await notebooksStore.executeCell(
        currentNotebook.value.id,
        cell.cellId,
        cell.source,
      );
    } catch (err) {
      toastsStore.push(`Run failed: ${err?.message || err}`, "danger");
    }
  }
  // Advance the cursor.
  const next = cells[idx + 1];
  if (next) {
    editorRef.value.setPosition({
      lineNumber: next.sourceStartLine,
      column: 1,
    });
    editorRef.value.revealLineInCenterIfOutsideViewport(next.sourceStartLine);
  }
}

// Per-cell run — invoked from the output panel's run button. Bypasses the
// cursor entirely so users don't have to chase it.
async function runCellById(cellId) {
  if (!currentNotebook.value || isLibrary.value) return;
  const model = models.get(currentNotebook.value.id);
  if (!model) return;
  const cell = parseCells(model.getValue()).find((c) => c.cellId === cellId);
  if (!cell || cell.type !== "code") return;
  await flushSave(currentNotebook.value.id);
  try {
    await notebooksStore.executeCell(
      currentNotebook.value.id,
      cell.cellId,
      cell.source,
    );
  } catch (err) {
    toastsStore.push(`Run failed: ${err?.message || err}`, "danger");
  }
}

// Insert a new code or markdown cell after the cell at the cursor (or at the
// end of the document if the cursor isn't inside a cell). Uses Monaco's edit
// API so undo/redo and onDidChangeContent (auto-save) all behave correctly.
function insertCell(type) {
  if (!currentNotebook.value || readOnly.value || isLibrary.value) return;
  if (!editorRef.value || !monaco.value) return;
  const model = models.get(currentNotebook.value.id);
  if (!model) return;

  const cells = parseCells(model.getValue());
  const pos = editorRef.value.getPosition();
  let endLine = model.getLineCount();
  if (pos && cells.length > 0) {
    const cell = findCellAtLine(cells, pos.lineNumber);
    if (cell) endLine = cell.sourceEndLine;
  }

  const lineLen = model.getLineContent(endLine).length;
  // Don't prepend a newline when the doc is a single empty line — otherwise
  // we'd seed a permanent leading blank line.
  const isEmptyDoc = endLine === 1 && lineLen === 0;
  const delimiter = `# %% [id=${uuid()}] ${type}\n`;
  const text = (isEmptyDoc ? "" : "\n") + delimiter;

  const range = new monaco.value.Range(
    endLine,
    lineLen + 1,
    endLine,
    lineLen + 1,
  );
  editorRef.value.executeEdits("insert-cell", [
    { range, text, forceMoveMarkers: true },
  ]);

  const cursorLine = isEmptyDoc ? 2 : endLine + 2;
  editorRef.value.setPosition({ lineNumber: cursorLine, column: 1 });
  editorRef.value.revealLineInCenterIfOutsideViewport(cursorLine);
  editorRef.value.focus();
}

async function clearOutputs() {
  if (!currentNotebook.value) return;
  if (!confirm("Clear all outputs from this notebook?")) return;
  try {
    await notebooksStore.clearOutputs(currentNotebook.value.id);
    toastsStore.push("Outputs cleared.", "success");
  } catch (err) {
    toastsStore.push(`Clear failed: ${err?.message || err}`, "danger");
  }
}

async function runAll() {
  if (!currentNotebook.value || isLibrary.value) return;
  await flushSave(currentNotebook.value.id);
  try {
    await notebooksStore.executeAll(currentNotebook.value.id);
  } catch (err) {
    toastsStore.push(`Run-all failed: ${err?.message || err}`, "danger");
  }
}

async function interrupt() {
  if (!currentNotebook.value) return;
  try {
    await notebooksStore.interruptKernel(currentNotebook.value.id);
  } catch (err) {
    toastsStore.push(`Interrupt failed: ${err?.message || err}`, "danger");
  }
}

async function restart() {
  if (!currentNotebook.value) return;
  if (!confirm("Restart kernel? All in-memory state will be lost.")) return;
  try {
    await notebooksStore.shutdownKernel(currentNotebook.value.id);
    toastsStore.push("Kernel will restart on next run.", "info");
  } catch (err) {
    toastsStore.push(`Restart failed: ${err?.message || err}`, "danger");
  }
}

async function fork() {
  if (!currentNotebook.value) return;
  try {
    const fork = await notebooksStore.forkNotebook(currentNotebook.value.id);
    toastsStore.push(`Forked to "${fork.name}".`, "success");
    emit("select-notebook", fork);
  } catch (err) {
    toastsStore.push(`Fork failed: ${err?.message || err}`, "danger");
  }
}

async function exportIpynb() {
  if (!currentNotebook.value) return;
  await flushSave(currentNotebook.value.id);
  try {
    const blob = await notebooksStore.exportNotebook(currentNotebook.value.id);
    const json = JSON.stringify(blob, null, 1);
    const file = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(file);
    const a = document.createElement("a");
    const safeName =
      (currentNotebook.value.name || "notebook").replace(/[^\w.-]+/g, "_") ||
      "notebook";
    a.href = url;
    a.download = `${safeName}.ipynb`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    toastsStore.push(`Export failed: ${err?.message || err}`, "danger");
  }
}

// ── Jump-to-cell from the output panel ──────────────────────────────────

function jumpToCell(cellId) {
  if (!editorRef.value) return;
  const model = models.get(currentNotebook.value?.id);
  if (!model) return;
  const cells = parseCells(model.getValue());
  const cell = cells.find((c) => c.cellId === cellId);
  if (!cell) return;
  // Switch to a mode where the editor is visible if it's hidden.
  if (viewMode.value === "output") viewMode.value = "split";
  editorRef.value.revealLineInCenter(cell.sourceStartLine);
  editorRef.value.setPosition({
    lineNumber: cell.sourceStartLine,
    column: 1,
  });
  editorRef.value.focus();
}

const saveLabel = computed(() => {
  switch (currentSaveStatus.value) {
    case "saving":
      return "Saving…";
    case "saved":
      return "Saved";
    case "error":
      return "Save failed";
    default:
      return "";
  }
});
</script>

<template>
  <section class="notebook-editor d-flex flex-column h-100 flex-grow-1">
    <div
      class="editor-toolbar border-bottom px-3 py-2 d-flex align-items-center gap-2 flex-wrap"
    >
      <template v-if="currentNotebook">
        <strong class="me-2">{{ currentNotebook.name }}</strong>
        <span
          class="badge me-1"
          :class="{
            'bg-info': currentNotebook.visibility === 'global',
            'bg-warning text-dark': currentNotebook.visibility === 'library',
            'bg-secondary': currentNotebook.visibility === 'personal',
          }"
          >{{ currentNotebook.visibility }}</span
        >
        <span
          v-if="readOnly && !isLibrary"
          class="badge bg-warning-subtle text-warning-emphasis me-1"
        >
          read-only
        </span>
        <small class="text-muted" v-if="saveLabel">{{ saveLabel }}</small>

        <!-- View-mode toggle -->
        <div
          class="btn-group btn-group-sm ms-3"
          role="group"
          aria-label="View mode"
        >
          <button
            type="button"
            class="btn btn-outline-secondary"
            :class="{ active: viewMode === 'code' }"
            title="Code only"
            @click="viewMode = 'code'"
          >
            <FontAwesomeIcon :icon="faCode" />
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :class="{ active: viewMode === 'split' }"
            title="Split"
            @click="viewMode = 'split'"
          >
            <FontAwesomeIcon :icon="faColumns" />
          </button>
          <button
            type="button"
            class="btn btn-outline-secondary"
            :class="{ active: viewMode === 'output' }"
            title="Output only"
            @click="viewMode = 'output'"
          >
            <FontAwesomeIcon :icon="faTableList" />
          </button>
        </div>

        <div class="ms-auto d-flex align-items-center gap-2">
          <KernelStatusPill
            v-if="!isLibrary"
            :status="kernelStatus"
            @interrupt="interrupt"
            @restart="restart"
          />
          <button
            v-if="!isLibrary"
            class="btn btn-outline-primary btn-sm"
            :disabled="kernelBusy"
            @click="runCell"
            title="Run the cell at the cursor"
          >
            <FontAwesomeIcon :icon="faPlay" class="me-1" />
            Run cell
          </button>
          <button
            v-if="!isLibrary && !kernelBusy"
            class="btn btn-outline-secondary btn-sm"
            @click="runAll"
            title="Run all code cells in order"
          >
            <FontAwesomeIcon :icon="faForwardStep" class="me-1" />
            Run all
          </button>
          <button
            v-if="!isLibrary && isOwner"
            class="btn btn-outline-secondary btn-sm"
            @click="clearOutputs"
            title="Clear all outputs from this notebook"
          >
            <FontAwesomeIcon :icon="faBroom" class="me-1" />
            Clear outputs
          </button>
          <button
            class="btn btn-outline-secondary btn-sm"
            @click="exportIpynb"
            title="Download as .ipynb"
          >
            <FontAwesomeIcon :icon="faDownload" class="me-1" />
            Export
          </button>
          <button
            v-if="readOnly"
            class="btn btn-outline-info btn-sm"
            @click="fork"
            title="Fork to a writable personal copy"
          >
            <FontAwesomeIcon :icon="faCodeBranch" class="me-1" />
            Fork to personal
          </button>
        </div>
      </template>
      <template v-else>
        <small class="text-muted">Select a notebook from the tree.</small>
      </template>
    </div>

    <MwctipyReferenceModal modal-id="mwctipyDocsModal" />

    <div
      v-if="isLibrary"
      class="alert alert-warning d-flex align-items-center gap-2 mb-0 rounded-0 py-2 px-3 small"
    >
      <FontAwesomeIcon :icon="faCodeBranch" />
      <span class="me-auto">
        This is a library notebook — read-only and not runnable. Fork it to a
        personal copy to edit and execute.
      </span>
      <button class="btn btn-sm btn-warning" @click="fork">
        <FontAwesomeIcon :icon="faCodeBranch" class="me-1" />
        Fork to personal
      </button>
    </div>

    <div class="editor-body flex-grow-1 d-flex">
      <div
        v-if="!currentNotebook && !loading"
        class="d-flex align-items-center justify-content-center text-muted flex-grow-1"
      >
        Pick a notebook on the left, or create a new one.
      </div>

      <div
        v-show="currentNotebook && showEditor"
        class="editor-pane"
        :class="{ 'editor-pane-split': showOutputs }"
      >
        <div
          class="editor-pane-toolbar border-bottom px-2 py-1 d-flex align-items-center gap-2"
        >
          <small class="text-muted font-monospace me-auto">python</small>
          <div v-if="!readOnly" class="dropdown">
            <button
              type="button"
              class="btn btn-outline-secondary btn-sm dropdown-toggle"
              data-bs-toggle="dropdown"
              aria-expanded="false"
              title="Add a new cell after the current cell"
            >
              <FontAwesomeIcon :icon="faPlus" class="me-1" />
              Add
            </button>
            <ul class="dropdown-menu dropdown-menu-end">
              <li>
                <button
                  type="button"
                  class="dropdown-item"
                  @click="insertCell('code')"
                >
                  <FontAwesomeIcon :icon="faCode" class="me-2" />
                  Code
                </button>
              </li>
              <li>
                <button
                  type="button"
                  class="dropdown-item"
                  @click="insertCell('markdown')"
                >
                  <FontAwesomeIcon :icon="faFileLines" class="me-2" />
                  Markdown
                </button>
              </li>
            </ul>
          </div>
          <button
            class="btn btn-outline-secondary btn-sm"
            data-bs-toggle="modal"
            data-bs-target="#mwctipyDocsModal"
            title="mwctipy reference (mwlab.* and render.*)"
          >
            <FontAwesomeIcon :icon="faBook" class="me-1" />
            mwctipy
          </button>
        </div>
        <div class="editor-pane-body flex-grow-1">
          <VueMonacoEditor
            language="python"
            :theme="monacoTheme"
            :options="monacoOptions"
            height="100%"
            @mount="onEditorMount"
          />
        </div>
      </div>

      <OutputPanel
        v-if="currentNotebook && showOutputs"
        :class="
          showEditor ? 'output-pane-split' : 'output-pane-full flex-grow-1'
        "
        :source="trackedSource"
        :cell-outputs="liveCellOutputs"
        :cell-meta="liveCellMeta"
        :kernel-busy="kernelBusy"
        :runnable="!isLibrary"
        @jump-to-cell="jumpToCell"
        @run-cell="runCellById"
      />
    </div>
  </section>
</template>

<style scoped>
.notebook-editor {
  flex: 1 1 0%;
  min-width: 0;
}
.editor-body {
  min-height: 0;
}
.editor-pane {
  flex: 1 1 0%;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.editor-pane-split {
  flex: 1 1 50%;
}
.editor-pane-toolbar {
  background: var(--bs-tertiary-bg, #f8f9fa);
}
.editor-pane-body {
  min-height: 0;
}
.output-pane-split {
  flex: 1 1 50%;
  min-width: 0;
}
.output-pane-full {
  min-width: 0;
}
</style>
