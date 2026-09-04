<script setup>
/**
 * MISP's event graph: the event as a root node, with its attributes, objects,
 * tags and galaxies hanging off it, and object references drawn as edges.
 *
 * The picture is built by pivotick-graph-transformer, which reads MISP's own
 * event JSON - so the event is fetched in that shape (`GET /events/{uuid}/
 * misp-json`, the same `to_misp_format()` used to push to a remote MISP)
 * rather than teaching the importer a second schema.
 */
import { computed, ref, watch } from "vue";
import { GraphRegistry } from "pivotick-transformer";
// Side-effect import: registers the MISP importer with the registry above.
import "pivotick-transformer/misp";
import PivotickGraph from "@/components/graph/PivotickGraph.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { useBootstrapTheme } from "@/helpers";
import { useEventsStore } from "@/stores";
import { router } from "@/router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faDiagramProject } from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
  event_uuid: {
    type: String,
    required: true,
  },
});

/**
 * The importer's three ways of drawing the same event. A large event is
 * unreadable in `detailed`, which is why this is a control and not a constant.
 */
const VIEW_MODES = [
  {
    id: "detailed",
    label: "Detailed",
    hint: "Every attribute, object and tag as its own node.",
  },
  {
    id: "grouped",
    label: "Grouped",
    hint: "Attributes and tags collapse behind one expandable node each.",
  },
  {
    id: "relations",
    label: "Relations",
    hint: "Only what takes part in an object reference. No event root, no tags.",
  },
];

/** Where a double click on a node goes, by the importer's own node type. */
const ROUTE_BY_NODE_TYPE = {
  "misp-attribute": "/attributes",
  "misp-object": "/objects",
  "misp-event": "/events",
};

const eventsStore = useEventsStore();
const theme = useBootstrapTheme();

const viewMode = ref("detailed");
const mispEvent = ref(null);
const loading = ref(false);
const error = ref(null);

async function load() {
  loading.value = true;
  error.value = null;

  try {
    mispEvent.value = await eventsStore.mispJson(props.event_uuid);
  } catch (err) {
    error.value = err;
    mispEvent.value = null;
  } finally {
    loading.value = false;
  }
}

load();
watch(() => props.event_uuid, load);

const graph = computed(() => {
  if (!mispEvent.value) {
    return { nodes: [], edges: [], notes: [] };
  }

  const { nodes, edges, notes } = GraphRegistry.getImporter("misp").convert(
    mispEvent.value,
    { theme: theme.value, viewMode: viewMode.value },
  );

  // The importer has no opinion on where a node lives in *this* app, so the
  // route is attached here - the wrapper opens `data.route` on a double click.
  return {
    nodes: nodes.map((node) => {
      const base = ROUTE_BY_NODE_TYPE[node.data?.type];

      return base
        ? { ...node, data: { ...node.data, route: `${base}/${node.id}` } }
        : node;
    }),
    edges,
    notes: notes ?? [],
  };
});

const nodeCount = computed(() => graph.value.nodes.length);

const tooltip = {
  title: (node) => node.getData()?.label,
  // The importer's node types are namespaced ("misp-galaxy-cluster"); the
  // namespace is noise in a hover card that is already inside a MISP event.
  subtitle: (node) =>
    String(node.getData()?.type ?? "")
      .replace(/^misp-/, "")
      .replace(/-/g, " "),
};

function open(route) {
  router.push(route);
}
</script>

<template>
  <div class="card">
    <div class="card-header d-flex flex-wrap align-items-center gap-2">
      <span class="me-auto">
        <FontAwesomeIcon :icon="faDiagramProject" /> Event Graph
      </span>
      <span v-if="!loading && !error" class="text-body-secondary small">
        {{ nodeCount }} node{{ nodeCount === 1 ? "" : "s" }}
      </span>
      <div class="btn-group btn-group-sm" role="group" aria-label="Graph view">
        <button
          v-for="mode in VIEW_MODES"
          :key="mode.id"
          type="button"
          class="btn"
          :class="
            viewMode === mode.id ? 'btn-primary' : 'btn-outline-secondary'
          "
          :title="mode.hint"
          :aria-pressed="viewMode === mode.id"
          @click="viewMode = mode.id"
        >
          {{ mode.label }}
        </button>
      </div>
    </div>
    <div class="card-body">
      <Spinner v-if="loading" />
      <div v-else-if="error" class="text-danger">
        Error loading event graph: {{ error }}
      </div>
      <template v-else>
        <PivotickGraph
          :key="viewMode"
          :nodes="graph.nodes"
          :edges="graph.edges"
          :notes="graph.notes"
          :tooltip="tooltip"
          click-action="inspect"
          height="min(75vh, 40rem)"
          @navigate="open"
        />
        <p class="text-body-secondary small mt-2 mb-0">
          Click a node for its details, double click to open it.
        </p>
      </template>
    </div>
  </div>
</template>
