<script setup>
/**
 * Canvas wrapper around pivotick: owns the instance lifecycle, the theme
 * rebuild and the teardown, so each graph view only has to describe its nodes,
 * edges and styles.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { Pivotick } from "pivotick";
import "pivotick/dist/pivotick.css";

const props = defineProps({
  nodes: {
    type: Array,
    required: true,
  },
  edges: {
    type: Array,
    default: () => [],
  },
  /** Per node-kind styles, keyed by the `kind` on each node's data. */
  nodeStyleMap: {
    type: Object,
    required: true,
  },
  edgeStyle: {
    type: Object,
    default: () => ({}),
  },
  isDirected: {
    type: Boolean,
    default: true,
  },
  /** `{ title, subtitle }` accessors for the hover card. */
  tooltip: {
    type: Object,
    default: null,
  },
  height: {
    type: String,
    default: "min(60vh, 30rem)",
  },
  /** Simulation overrides merged over the defaults below. */
  simulation: {
    type: Object,
    default: () => ({}),
  },
});

const emit = defineEmits(["navigate"]);

const canvas = ref(null);
const theme = ref(readTheme());

let graph = null;
let themeObserver = null;

function readTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "dark"
    : "light";
}

const data = computed(() => ({ nodes: props.nodes, edges: props.edges }));

function buildOptions() {
  return {
    isDirected: props.isDirected,
    simulation: {
      // These graphs are small; the worker only adds a chunk to load and a
      // console warning when it cannot be spawned.
      useWorker: false,
      // The defaults pack nodes tightly, which collides the labels these
      // graphs exist to show. Longer links and more repulsion buy them room.
      d3LinkDistance: 110,
      d3ManyBodyStrength: -600,
      d3CollideRadiusMultiplier: 2.4,
      ...props.simulation,
      callbacks: {
        // Spreading the layout pushes nodes past the initial viewport, so the
        // view is refit once the simulation comes to rest.
        onStop: () => graph?.renderer?.fitAndCenterWhenSettled(),
      },
    },
    render: {
      type: "svg",
      nodeTypeAccessor: (node) => node.getData()?.kind,
      nodeStyleMap: props.nodeStyleMap,
      defaultEdgeStyle: props.edgeStyle,
    },
    UI: {
      mode: "viewer",
      theme: theme.value,
      ...(props.tooltip
        ? {
            tooltip: {
              nodeHeaderMap: {
                title: (node) => String(props.tooltip.title(node) ?? ""),
                subtitle: (node) => String(props.tooltip.subtitle(node) ?? ""),
              },
            },
          }
        : {}),
    },
    callbacks: {
      onNodeClick: (_pointerEvent, node) => {
        const route = node.getData()?.route;

        if (route) {
          emit("navigate", route);
        }
      },
    },
  };
}

function render() {
  if (!canvas.value) {
    return;
  }

  destroy();

  graph = new Pivotick(canvas.value, data.value, buildOptions());
}

function destroy() {
  graph?.destroy();
  graph = null;

  // destroy() tears down the UI and the renderer but leaves behind the
  // container div the constructor appended, so it is removed here to keep
  // re-renders from stacking canvases.
  canvas.value?.replaceChildren();
}

onMounted(() => {
  render();

  // The app switches themes by swapping data-bs-theme on <html>, which the
  // library reads once at construction, so the graph is rebuilt on a change.
  themeObserver = new MutationObserver(() => {
    const next = readTheme();

    if (next !== theme.value) {
      theme.value = next;
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
  destroy();
});

watch([data, theme], () => render());
</script>

<template>
  <div
    ref="canvas"
    class="pivotick-canvas"
    :style="{ height: props.height }"
  ></div>
</template>

<style scoped>
.pivotick-canvas {
  border: 1px solid var(--bs-border-color);
  border-radius: var(--bs-border-radius);
  overflow: hidden;
}

/* The library sizes itself to its container. */
.pivotick-canvas :deep(.pivotick) {
  width: 100%;
  height: 100%;
}
</style>
