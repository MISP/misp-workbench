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
  /**
   * Hover card: `{ title, subtitle }` accessors, plus an optional `body(node)`
   * returning an element. The element is handed to the library as is, so a
   * caller can keep the reference and fill it in once an async lookup lands.
   */
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
  /**
   * Where a node can be expanded, a click expands it and a double click opens
   * it. The library fires click and dblclick independently, so the expansion is
   * held back briefly and dropped if a double click follows - otherwise
   * double clicking would also expand on its way out. The wait is invisible
   * here because expanding goes on to fetch anyway.
   *
   * Graphs with nothing to expand keep click to open, since there is no second
   * action to disambiguate from.
   */
  expandable: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["navigate", "expand"]);

// Long enough to catch the second click of a double click.
const DOUBLE_CLICK_GRACE = 250;

const canvas = ref(null);
const theme = ref(readTheme());

let graph = null;
let themeObserver = null;
let expandTimer = null;
// What the live instance currently holds, so growth can be applied in place.
let rendered = { nodes: new Set(), edges: new Set() };

function edgeId(edge) {
  return String(edge.id ?? `${edge.from}|${edge.to}`);
}

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
              ...(props.tooltip.body
                ? { render: (node) => props.tooltip.body(node) }
                : {}),
            },
          }
        : {}),
    },
    callbacks: {
      onNodeClick: (_pointerEvent, node) => {
        if (!props.expandable) {
          const route = node.getData()?.route;

          if (route) {
            emit("navigate", route);
          }

          return;
        }

        // The position travels with the data so new nodes can be seeded beside
        // the node they came from instead of flying in from the origin.
        const payload = { ...node.getData(), x: node.x, y: node.y };

        clearTimeout(expandTimer);
        expandTimer = setTimeout(
          () => emit("expand", payload),
          DOUBLE_CLICK_GRACE,
        );
      },
      onNodeDbclick: (_pointerEvent, node) => {
        clearTimeout(expandTimer);

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
  rendered = {
    nodes: new Set(props.nodes.map((node) => String(node.id))),
    edges: new Set(props.edges.map(edgeId)),
  };
}

/**
 * Apply a data change to the live instance where it only adds to what is on
 * screen, which is what expanding a node does: the placed nodes keep their
 * positions and the new ones settle in beside them. Anything else - a different
 * subject, a filter, a mode switch - is a different picture, so it is rebuilt.
 */
function sync() {
  if (!graph) {
    render();
    return;
  }

  const nodeIds = new Set(props.nodes.map((node) => String(node.id)));
  const edgeIds = new Set(props.edges.map(edgeId));

  const onlyAdded =
    [...rendered.nodes].every((id) => nodeIds.has(id)) &&
    [...rendered.edges].every((id) => edgeIds.has(id));

  if (!onlyAdded) {
    render();
    return;
  }

  for (const node of props.nodes) {
    if (!rendered.nodes.has(String(node.id))) {
      graph.addNode(node);
      rendered.nodes.add(String(node.id));
    }
  }

  // After the nodes: an edge needs both of its endpoints to exist.
  for (const edge of props.edges) {
    const id = edgeId(edge);

    if (!rendered.edges.has(id)) {
      graph.addEdge({ ...edge, id });
      rendered.edges.add(id);
    }
  }
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
  clearTimeout(expandTimer);
  destroy();
});

watch(theme, () => render());
watch(data, () => sync());
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

/* The library highlights the selected node in red, which reads as an error
   here - selection only means "the one you just acted on". The variable has to
   be set on .pivotick itself, since that is where the library's own theme block
   defines it; an inherited value from the parent would lose. */
.pivotick-canvas :deep(.pivotick[data-theme]) {
  --pvt-node-selected-color: var(--bs-primary);
  --pvt-node-selected-stroke: var(--bs-primary);
}

/* The library sizes itself to its container. */
.pivotick-canvas :deep(.pivotick) {
  width: 100%;
  height: 100%;
}
</style>
