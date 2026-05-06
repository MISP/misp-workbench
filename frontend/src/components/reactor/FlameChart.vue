<script setup>
import { ref, watch, onBeforeUnmount, computed, nextTick, toRaw } from "vue";
// d3-flame-graph exports the factory as default — there is no named
// `flamegraph` export, so destructured imports fail at module-eval time.
import flamegraph from "d3-flame-graph";
import * as d3 from "d3";
// d3-flame-graph's package.json `exports` map only exposes the entrypoint,
// so its CSS file isn't importable as a subpath (Vite blocks deep imports
// past the exports map). Inline the (tiny) stylesheet below in <style> to
// keep the component self-contained.

const props = defineProps({
  // d3-flame-graph tree: { name, value, children }. Pass null to clear.
  tree: { type: Object, default: null },
  height: { type: Number, default: 320 },
});

const container = ref(null);
let chartInstance = null;
let resizeObserver = null;
const renderError = ref(null);

const totalSeconds = computed(() => Number(props.tree?.value || 0));

// d3-flame-graph collapses any subtree whose root has value=0 — pyinstrument
// emits a synthetic root frame whose `time` is 0 when the handler is too
// fast to sample. Patch the tree so the chart still renders something.
function ensureRootHasValue(node) {
  if (!node) return node;
  if (node.value > 0) return node;
  let total = 0;
  for (const c of node.children || []) total += Number(c.value || 0);
  return { ...node, value: total || 0.001 };
}

async function render() {
  renderError.value = null;
  if (!props.tree) return;
  // v-if mounts the wrapper this tick; wait one frame so `container` is
  // bound and the parent has laid out (clientWidth > 0).
  await nextTick();
  if (!container.value) return;

  // Strip Vue's reactive proxy — d3-flame-graph mutates its data and chokes
  // on get/set traps in some code paths.
  const data = ensureRootHasValue(
    JSON.parse(JSON.stringify(toRaw(props.tree))),
  );

  d3.select(container.value).selectAll("*").remove();

  const width =
    container.value.clientWidth ||
    container.value.parentElement?.clientWidth ||
    600;

  try {
    chartInstance = flamegraph()
      .width(width)
      .cellHeight(18)
      .minFrameSize(0.5)
      .transitionDuration(150)
      .sort(true)
      .selfValue(false)
      .label((node) => {
        const v = Number(node.data.value || 0);
        return `${node.data.name} — ${v.toFixed(3)}s`;
      });

    d3.select(container.value).datum(data).call(chartInstance);
  } catch (err) {
    renderError.value = err?.message || String(err);
    console.error("FlameChart render failed", err);
  }
}

function reset() {
  if (chartInstance) chartInstance.resetZoom();
}

// Re-render when the tree changes; ResizeObserver re-renders on width
// changes (e.g. side panel resize) so the bars stretch to fit.
watch(() => props.tree, render, { flush: "post", immediate: true });

watch(container, (el) => {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (!el) return;
  let lastWidth = el.clientWidth;
  resizeObserver = new ResizeObserver(() => {
    const w = el.clientWidth;
    if (w && w !== lastWidth) {
      lastWidth = w;
      render();
    }
  });
  resizeObserver.observe(el);
});

onBeforeUnmount(() => {
  if (resizeObserver) resizeObserver.disconnect();
  if (container.value) d3.select(container.value).selectAll("*").remove();
  chartInstance = null;
});
</script>

<template>
  <div v-if="tree">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <small class="text-muted">
        Flame chart — {{ totalSeconds.toFixed(3) }}s total. Click a frame to
        zoom; click root to reset.
      </small>
      <button class="btn btn-link btn-sm p-0" @click="reset">Reset zoom</button>
    </div>
    <div
      ref="container"
      class="reactor-flame-chart border rounded"
      :style="{ minHeight: `${height}px` }"
    />
    <div v-if="renderError" class="alert alert-warning small mt-2 mb-0">
      Flame chart render failed: {{ renderError }}
    </div>
  </div>
</template>

<style scoped>
.reactor-flame-chart {
  overflow-x: auto;
}
</style>

<style>
/* Inlined from d3-flame-graph/dist/d3-flamegraph.css — see comment in
   <script setup> for why we don't import it directly. Unscoped because
   d3-flame-graph adds these classes to SVG nodes it injects at runtime. */
.d3-flame-graph rect {
  stroke: #eee;
  fill-opacity: 0.8;
}
.d3-flame-graph rect:hover {
  stroke: #474747;
  stroke-width: 0.5;
  cursor: pointer;
}
.d3-flame-graph-label {
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  font-size: 12px;
  font-family: Verdana;
  margin-left: 4px;
  margin-right: 4px;
  line-height: 1.5;
  padding: 0;
  font-weight: 400;
  color: #000;
  text-align: left;
}
.d3-flame-graph .fade {
  opacity: 0.6 !important;
}
.d3-flame-graph .title {
  font-size: 20px;
  font-family: Verdana;
}
.d3-flame-graph-tip {
  background-color: #000;
  border: none;
  border-radius: 3px;
  padding: 5px 10px;
  min-width: 250px;
  text-align: left;
  color: #fff;
  z-index: 10;
}
</style>
