<script setup>
import { computed } from "vue";
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import CellOutput from "./CellOutput.vue";
import { parseCells } from "./cellDelimiterParser";

const props = defineProps({
  source: { type: String, default: "" },
  cellOutputs: { type: Object, default: () => ({}) },
  cellMeta: { type: Object, default: () => ({}) },
  kernelBusy: { type: Boolean, default: false },
});

const emit = defineEmits(["jump-to-cell", "run-cell"]);

// Re-parse on every render so the panel stays in sync with the editor's
// current cell ids — when a cell is renamed or reordered we want its outputs
// to follow the source ordering even if the cell ids change.
const cells = computed(() => parseCells(props.source));

const cellsWithOutputs = computed(() =>
  cells.value
    .map((c, idx) => ({
      cellId: c.cellId,
      idx,
      type: c.type,
      sourcePreview: previewLine(c.source),
      outputs: props.cellOutputs[c.cellId] || [],
      meta: props.cellMeta[c.cellId] || null,
    }))
    .filter((c) => c.outputs.length > 0 || c.meta != null),
);

function formatDuration(ms) {
  if (ms == null) return "";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 2 : 1)} s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds - minutes * 60;
  return `${minutes}m ${rem.toFixed(0)}s`;
}

function previewLine(source) {
  const firstNonEmpty = (source || "")
    .split("\n")
    .map((l) => l.trim())
    .find((l) => l.length > 0);
  if (!firstNonEmpty) return "(empty)";
  return firstNonEmpty.length > 80
    ? firstNonEmpty.slice(0, 80) + "…"
    : firstNonEmpty;
}

function jump(cellId) {
  emit("jump-to-cell", cellId);
}

function run(cellId) {
  emit("run-cell", cellId);
}
</script>

<template>
  <aside class="output-panel d-flex flex-column h-100">
    <div class="output-panel-header border-bottom px-3 py-2">
      <strong class="small text-muted me-auto">Outputs</strong>
    </div>
    <div class="output-panel-body flex-grow-1 overflow-auto">
      <div
        v-if="cellsWithOutputs.length === 0"
        class="text-muted small p-3 fst-italic"
      >
        No outputs yet — run a cell to see results here.
      </div>
      <div
        v-for="cell in cellsWithOutputs"
        :key="cell.cellId"
        class="output-block"
      >
        <div
          class="output-block-header d-flex align-items-center gap-2 px-2 py-1"
        >
          <span class="badge bg-secondary">{{ cell.idx + 1 }}</span>
          <code
            class="small text-truncate flex-grow-1 jumpable"
            role="button"
            @click="jump(cell.cellId)"
            :title="`Jump to cell ${cell.idx + 1}`"
            >{{ cell.sourcePreview }}</code
          >
          <button
            v-if="cell.type === 'code'"
            class="btn btn-link btn-sm p-0 text-primary"
            :disabled="kernelBusy"
            @click.stop="run(cell.cellId)"
            :title="`Run cell ${cell.idx + 1}`"
          >
            <FontAwesomeIcon :icon="faPlay" />
          </button>
        </div>
        <CellOutput :outputs="cell.outputs" />
        <div v-if="cell.meta" class="output-block-footer px-2 py-1 small">
          <span
            v-if="cell.meta.status === 'error'"
            class="text-danger me-2"
            title="Cell raised an exception"
            >errored</span
          >
          <span
            v-else-if="cell.meta.status === 'interrupted'"
            class="text-warning me-2"
            title="Cell was interrupted"
            >interrupted</span
          >
          <span class="text-muted">
            took {{ formatDuration(cell.meta.durationMs) }}
          </span>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.output-panel {
  border-left: 1px solid var(--bs-border-color, #dee2e6);
  background: var(--bs-body-bg, #fff);
  min-width: 0;
}
.output-panel-header {
  background: var(--bs-tertiary-bg, #f8f9fa);
}
.output-block {
  border-bottom: 1px solid var(--bs-border-color, #dee2e6);
}
.output-block:last-child {
  border-bottom: 0;
}
.output-block-header {
  background: var(--bs-tertiary-bg, #f8f9fa);
  font-size: 0.75rem;
}
.output-block-header .jumpable {
  cursor: pointer;
}
.output-block-header .jumpable:hover {
  text-decoration: underline;
}
.output-block-footer {
  background: var(--bs-tertiary-bg, #f8f9fa);
  border-top: 1px solid var(--bs-border-color, #dee2e6);
  font-size: 0.75rem;
}
</style>
