<script setup>
/**
 * Which events are tied together by the indicators they share. The stats
 * endpoint only returns per entity counts, so the pairs are read from the
 * correlation documents themselves and folded into an event to event network.
 */
import { computed, onMounted, ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSitemap } from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import GraphLegend from "@/components/correlations/GraphLegend.vue";
import PivotickGraph from "@/components/correlations/PivotickGraph.vue";
import { useCorrelationsStore } from "@/stores";

const emit = defineEmits(["navigate"]);

// The search endpoint caps a page at 100 documents; three of them is a big
// enough sample to show the shape of the network without stalling the view.
const SAMPLE_PAGES = 3;
const SAMPLE_PAGE_SIZE = 100;
const EVENT_COLOR = "#6c757d";

const correlationsStore = useCorrelationsStore();

const documents = ref([]);
const total = ref(0);
const loading = ref(true);
const error = ref(null);

onMounted(async () => {
  try {
    const sample = await correlationsStore.sample({
      pages: SAMPLE_PAGES,
      size: SAMPLE_PAGE_SIZE,
    });

    documents.value = sample.results;
    total.value = sample.total;
  } catch (caught) {
    error.value = caught;
  } finally {
    loading.value = false;
  }
});

function shortUuid(uuid) {
  return String(uuid ?? "").slice(0, 8);
}

/**
 * Correlations are stored once per direction, so a pair of events shows up
 * twice. Both the event weights and the edge weights count distinct pairs of
 * attributes, which keeps a mutual correlation from counting double.
 */
const network = computed(() => {
  const events = new Map();
  const links = new Map();

  for (const document of documents.value) {
    const source = document._source;
    const sourceEvent = source.source_event_uuid;
    const targetEvent = source.target_event_uuid;

    if (!sourceEvent || !targetEvent || sourceEvent === targetEvent) {
      continue;
    }

    const [left, right] = [sourceEvent, targetEvent].sort();
    const attributePair = [
      source.source_attribute_uuid,
      source.target_attribute_uuid,
    ]
      .sort()
      .join("|");

    let link = links.get(`${left}|${right}`);
    if (!link) {
      link = { from: left, to: right, shared: new Set() };
      links.set(`${left}|${right}`, link);
    }
    link.shared.add(attributePair);

    for (const uuid of [left, right]) {
      let event = events.get(uuid);
      if (!event) {
        event = { uuid, shared: new Set() };
        events.set(uuid, event);
      }
      event.shared.add(attributePair);
    }
  }

  return {
    events: [...events.values()],
    links: [...links.values()],
  };
});

const graphData = computed(() => ({
  nodes: network.value.events.map((event) => ({
    id: event.uuid,
    data: {
      kind: "event",
      label: shortUuid(event.uuid),
      uuid: event.uuid,
      weight: event.shared.size,
      route: `/events/${event.uuid}`,
    },
  })),
  edges: network.value.links.map((link) => ({
    from: link.from,
    to: link.to,
    data: { weight: link.shared.size },
  })),
}));

const sharedIndicators = computed(() =>
  network.value.links.reduce((total, link) => total + link.shared.size, 0),
);

const sampled = computed(() => documents.value.length);

const nodeStyleMap = {
  event: {
    shape: "square",
    // Sized by how many shared indicators the event takes part in. Square root
    // so the area, not the side, carries the weight.
    size: (node) =>
      11 + Math.min(13, Math.sqrt(node.getData()?.weight ?? 1) * 3),
    color: EVENT_COLOR,
    text: (node) => node.getData()?.label,
    textVerticalShift: 1,
  },
};

// Function valued fields, not styleCb: the drawer only consults styleCb for a
// style set on an individual edge, while these resolve per edge from the
// renderer defaults.
const edgeStyle = {
  strokeWidth: (edge) => 1 + Math.min(6, edge.getData()?.weight ?? 1),
  opacity: 0.75,
};

const legendItems = [
  { shape: "square", color: EVENT_COLOR, label: "event · bigger shares more" },
  { shape: "line", label: "shared indicators · thicker shares more" },
];

const tooltip = {
  title: (node) => node.getData()?.uuid,
  subtitle: (node) => {
    const weight = node.getData()?.weight ?? 0;

    return `${weight} shared ${weight === 1 ? "indicator" : "indicators"}`;
  },
};
</script>

<template>
  <div v-if="error" class="alert alert-danger">
    <ApiError :errors="error" />
  </div>

  <div v-else-if="loading" class="text-center py-5">
    <div class="spinner-border text-secondary" role="status">
      <span class="visually-hidden">Loading correlations…</span>
    </div>
  </div>

  <div v-else-if="!graphData.nodes.length" class="empty text-center py-5">
    <FontAwesomeIcon :icon="faSitemap" class="empty__icon mb-3" />
    <p class="mb-1">No connected events yet</p>
    <p class="text-body-secondary small mb-0">
      Correlations link events that share an indicator. None of the sampled
      correlations join two different events.
    </p>
  </div>

  <div v-else>
    <PivotickGraph
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :node-style-map="nodeStyleMap"
      :edge-style="edgeStyle"
      :is-directed="false"
      :tooltip="tooltip"
      height="min(70vh, 34rem)"
      @navigate="emit('navigate', $event)"
    />

    <GraphLegend class="mt-2" :items="legendItems" />

    <p class="graph-caption mb-0 mt-2">
      {{ graphData.nodes.length }} connected
      {{ graphData.nodes.length === 1 ? "event" : "events" }} &middot;
      {{ sharedIndicators }} shared
      {{ sharedIndicators === 1 ? "indicator" : "indicators" }} &middot; click a
      node to open it
      <template v-if="total > sampled">
        <br />
        Built from the {{ sampled.toLocaleString() }} most recent of
        {{ total.toLocaleString() }} correlations.
      </template>
    </p>
  </div>
</template>

<style scoped>
.graph-caption {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}

.empty__icon {
  font-size: 1.75rem;
  color: var(--bs-secondary-color);
  opacity: 0.6;
}
</style>
