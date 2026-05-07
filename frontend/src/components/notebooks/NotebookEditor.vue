<script setup>
import {
  ref,
  shallowRef,
  watch,
  computed,
  onMounted,
  onBeforeUnmount,
  createApp,
  h,
} from "vue";
import { storeToRefs } from "pinia";
import { useNotebooksStore, useToastsStore } from "@/stores";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import {
  faCodeBranch,
  faPlay,
  faForwardStep,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import CellOutput from "./CellOutput.vue";
import KernelStatusPill from "./KernelStatusPill.vue";
import { parseCells, findCellAtLine } from "./cellDelimiterParser";

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
} = storeToRefs(notebooksStore);

const editorRef = shallowRef(null);
const monaco = shallowRef(null);

// id → ITextModel (kept outside reactive state to preserve Monaco identity).
const models = new Map();

// notebookId → Map<cellId, { zoneId, dom, app, outputsRef, observer }>
const viewZonesByNotebook = new Map();

const currentNotebook = ref(null);
const loading = ref(false);

const isOwner = computed(() => {
  if (!currentNotebook.value || props.currentUserId == null) return false;
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
  // Tear down all view zones and their Vue apps.
  for (const map of viewZonesByNotebook.values()) {
    for (const z of map.values()) destroyZone(z);
  }
  viewZonesByNotebook.clear();
  // Dispose Monaco models.
  for (const m of models.values()) {
    try {
      m.dispose();
    } catch {
      /* noop */
    }
  }
  models.clear();
});

function onEditorMount(editor, monacoInstance) {
  editorRef.value = editor;
  monaco.value = monacoInstance;
  if (currentNotebook.value) {
    swapModel(currentNotebook.value);
  }
}

function ensureModelFor(notebook) {
  if (!monaco.value) return null;
  let model = models.get(notebook.id);
  if (!model) {
    model = monaco.value.editor.createModel(notebook.source || "", "python");
    models.set(notebook.id, model);
    model.onDidChangeContent(() => onModelChange(notebook.id));
  } else {
    if (notebook.source != null && model.getValue() !== notebook.source) {
      model.setValue(notebook.source);
    }
  }
  return model;
}

function swapModel(notebook) {
  if (!editorRef.value || !monaco.value) return;

  // Hide view zones from any other notebook before swapping.
  hideAllViewZones();

  const model = ensureModelFor(notebook);
  if (model) editorRef.value.setModel(model);

  // Render this notebook's cell outputs as view zones.
  syncViewZones(notebook.id);
}

// ── Auto-save (1s debounce per notebook) ────────────────────────────────

const _saveTimers = new Map();
function onModelChange(notebookId) {
  if (currentNotebook.value?.id !== notebookId) return;
  // Re-sync view zones immediately so cells added/removed reflect on screen
  // even before the source is persisted.
  syncViewZones(notebookId);
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

// ── View zones: one per cell, mounting CellOutput.vue ───────────────────

function getZoneMap(notebookId) {
  let map = viewZonesByNotebook.get(notebookId);
  if (!map) {
    map = new Map();
    viewZonesByNotebook.set(notebookId, map);
  }
  return map;
}

function destroyZone(zone) {
  try {
    zone.observer?.disconnect();
  } catch {
    /* noop */
  }
  try {
    zone.app?.unmount();
  } catch {
    /* noop */
  }
  // The DOM node is removed from layout when the editor disposes the zone;
  // we don't need to detach it manually.
}

function hideAllViewZones() {
  if (!editorRef.value) return;
  editorRef.value.changeViewZones((accessor) => {
    for (const map of viewZonesByNotebook.values()) {
      for (const zone of map.values()) {
        if (zone.zoneId != null) {
          try {
            accessor.removeZone(zone.zoneId);
          } catch {
            /* noop */
          }
          zone.zoneId = null;
        }
      }
    }
  });
}

// Re-parse the model and reconcile view zones with the cell list. Each
// cell gets one zone whose afterLineNumber sits at the cell's last source
// line; the zone's DOM hosts a Vue-mounted <CellOutput> bound to a
// reactive ref that tracks notebook.cell_outputs[cellId].
function syncViewZones(notebookId) {
  if (!editorRef.value || !monaco.value) return;
  const model = models.get(notebookId);
  if (!model) return;
  const nb = storeNotebooks.value[notebookId];
  if (!nb) return;

  const cells = parseCells(model.getValue());
  const liveIds = new Set(cells.map((c) => c.cellId));
  const zoneMap = getZoneMap(notebookId);

  editorRef.value.changeViewZones((accessor) => {
    // Remove zones for cells that no longer exist.
    for (const [cellId, zone] of zoneMap.entries()) {
      if (!liveIds.has(cellId)) {
        if (zone.zoneId != null) {
          try {
            accessor.removeZone(zone.zoneId);
          } catch {
            /* noop */
          }
        }
        destroyZone(zone);
        zoneMap.delete(cellId);
      }
    }

    // Add / update zones for current cells.
    for (const cell of cells) {
      let zone = zoneMap.get(cell.cellId);
      if (!zone) {
        zone = createZone(cell.cellId, nb.cell_outputs?.[cell.cellId] || []);
        zoneMap.set(cell.cellId, zone);
      } else {
        // Update outputs in case they changed since last sync.
        zone.outputsRef.value = nb.cell_outputs?.[cell.cellId] || [];
      }
      // (Re)place the zone after the cell's last source line.
      if (zone.zoneId != null) {
        try {
          accessor.removeZone(zone.zoneId);
        } catch {
          /* noop */
        }
      }
      const afterLine = Math.max(cell.sourceEndLine, cell.delimiterLine);
      zone.zoneId = accessor.addZone({
        afterLineNumber: afterLine,
        domNode: zone.dom,
        heightInPx: zone.dom.offsetHeight || 8,
      });
    }
  });
}

function createZone(cellId, initialOutputs) {
  const dom = document.createElement("div");
  dom.className = "lab-view-zone";
  // outputsRef must be reactive so updates re-render CellOutput.
  const outputsRef = ref(initialOutputs);
  const app = createApp({
    setup() {
      return () => h(CellOutput, { outputs: outputsRef.value });
    },
  });
  app.mount(dom);

  // Resize the zone whenever the rendered output changes height.
  let observer = null;
  if (typeof ResizeObserver !== "undefined") {
    observer = new ResizeObserver(() => {
      relayoutZone(cellId);
    });
    observer.observe(dom);
  }
  return { zoneId: null, dom, app, outputsRef, observer, cellId };
}

function relayoutZone(cellId) {
  if (!editorRef.value || !currentNotebook.value) return;
  const map = viewZonesByNotebook.get(currentNotebook.value.id);
  const zone = map?.get(cellId);
  if (!zone || zone.zoneId == null) return;
  editorRef.value.changeViewZones((accessor) => {
    try {
      accessor.layoutZone(zone.zoneId);
    } catch {
      /* noop */
    }
  });
}

// React to outputs changing (after a cell run completes) by pushing the new
// outputs into the matching zone's reactive ref.
watch(
  () => {
    const nb = currentNotebook.value;
    if (!nb) return null;
    const live = storeNotebooks.value[nb.id];
    return live?.cell_outputs;
  },
  (cellOutputs) => {
    if (!cellOutputs || !currentNotebook.value) return;
    const map = viewZonesByNotebook.get(currentNotebook.value.id);
    if (!map) return;
    for (const [cellId, zone] of map.entries()) {
      zone.outputsRef.value = cellOutputs[cellId] || [];
    }
  },
  { deep: true },
);

// ── React to notebook prop changes ──────────────────────────────────────

watch(
  () => props.notebookId,
  async (newId) => {
    if (newId == null) {
      currentNotebook.value = null;
      hideAllViewZones();
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
  if (!currentNotebook.value) return;
  const cell = cellAtCursor();
  if (!cell) {
    toastsStore.push("Place the cursor inside a code cell first.", "warning");
    return;
  }
  if (cell.type !== "code") {
    toastsStore.push("Markdown cells aren't executed.", "info");
    return;
  }
  // Save first so the server-side parse sees the latest source.
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

async function runAll() {
  if (!currentNotebook.value) return;
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
      class="editor-toolbar border-bottom px-3 py-2 d-flex align-items-center gap-2"
    >
      <template v-if="currentNotebook">
        <strong class="me-2">{{ currentNotebook.name }}</strong>
        <span
          class="badge me-1"
          :class="
            currentNotebook.visibility === 'global' ? 'bg-info' : 'bg-secondary'
          "
          >{{ currentNotebook.visibility }}</span
        >
        <span
          v-if="readOnly"
          class="badge bg-warning-subtle text-warning-emphasis me-1"
        >
          read-only
        </span>
        <small class="text-muted" v-if="saveLabel">{{ saveLabel }}</small>

        <div class="ms-auto d-flex align-items-center gap-2">
          <KernelStatusPill
            :status="kernelStatus"
            @interrupt="interrupt"
            @restart="restart"
          />

          <button
            class="btn btn-outline-primary btn-sm"
            :disabled="kernelBusy"
            @click="runCell"
            title="Run the cell at the cursor"
          >
            <FontAwesomeIcon :icon="faPlay" class="me-1" />
            Run cell
          </button>
          <button
            v-if="!kernelBusy"
            class="btn btn-outline-secondary btn-sm"
            @click="runAll"
            title="Run all code cells in order"
          >
            <FontAwesomeIcon :icon="faForwardStep" class="me-1" />
            Run all
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

    <div class="editor-body flex-grow-1 position-relative">
      <div
        v-if="!currentNotebook && !loading"
        class="d-flex align-items-center justify-content-center text-muted h-100"
      >
        Pick a notebook on the left, or create a new one.
      </div>
      <VueMonacoEditor
        v-show="currentNotebook"
        language="python"
        :theme="monacoTheme"
        :options="monacoOptions"
        height="100%"
        @mount="onEditorMount"
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
</style>

<style>
/* Global so the view-zone DOM (rendered outside the scoped tree) gets it. */
.lab-view-zone {
  width: 100%;
}
</style>
