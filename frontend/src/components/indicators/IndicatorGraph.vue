<script setup>
import { computed, ref, watch } from "vue";
import { router } from "@/router";
import GraphLegend from "@/components/correlations/GraphLegend.vue";
import PivotickGraph from "@/components/graph/PivotickGraph.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { useIndicatorsStore } from "@/stores";
import { buildIndicatorGraph } from "@/helpers/indicator-graph";

// What an indicator is derived from: the attributes it merges, the objects
// they sit in and the events holding them.
const props = defineProps({
  indicatorUuid: { type: String, required: true },
  height: { type: String, default: "min(55vh, 28rem)" },
});

const indicatorsStore = useIndicatorsStore();

// Labels are shortened here and drawn whole (textTruncate: false): the
// library's own truncation keeps a head and a tail, "Cobalt S…se…".
const LABEL_LENGTH = 28;
const INDICATOR_COLOR = "#0d6efd";
const ATTRIBUTE_COLOR = "#20c997";
const NON_IDS_COLOR = "#adb5bd";
const OBJECT_COLOR = "#fd7e14";
const EVENT_COLOR = "#6c757d";
const MORE_COLOR = "#dee2e6";

const graph = ref(null);
const loading = ref(false);
const error = ref(null);
// An object's other attributes: its context, collapsed by default.
const showSiblings = ref(false);

watch(
  () => props.indicatorUuid,
  async (uuid) => {
    graph.value = null;
    error.value = null;
    loading.value = true;
    try {
      graph.value = await indicatorsStore.graph(uuid);
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
  },
  { immediate: true },
);

const data = computed(() =>
  buildIndicatorGraph(graph.value, { showSiblings: showSiblings.value }),
);
const isEmpty = computed(() => !graph.value?.attributes.length);
const siblingCount = computed(() =>
  (graph.value?.objects || []).reduce((n, o) => n + o.attribute_count, 0),
);

function truncate(value) {
  const text = String(value ?? "");
  return text.length > LABEL_LENGTH
    ? `${text.slice(0, LABEL_LENGTH - 1)}…`
    : text;
}

const label = (node) => truncate(node.getData()?.label);
// The value is the indicator's: an attribute says how it was reported, as an
// object's relation or else its category.
const attributeLabel = (node) => {
  const attribute = node.getData()?.attribute;
  return truncate(attribute?.object_relation || attribute?.category);
};

const nodeStyleMap = {
  indicator: {
    shape: "hexagon",
    size: 26,
    color: INDICATOR_COLOR,
    text: label,
    textVerticalShift: -1,
    textTruncate: false,
  },
  attribute: {
    shape: "circle",
    size: 18,
    color: (node) =>
      node.getData()?.attribute?.to_ids ? ATTRIBUTE_COLOR : NON_IDS_COLOR,
    text: attributeLabel,
    textVerticalShift: -1,
    textTruncate: false,
  },
  sibling: {
    shape: "circle",
    size: 13,
    color: NON_IDS_COLOR,
    text: label,
    textVerticalShift: -1,
    textTruncate: false,
  },
  object: {
    shape: "triangle",
    size: 20,
    color: OBJECT_COLOR,
    text: label,
    textVerticalShift: 1,
    textTruncate: false,
  },
  event: {
    shape: "square",
    size: 18,
    color: EVENT_COLOR,
    text: label,
    textVerticalShift: 1,
    textTruncate: false,
  },
  more: {
    shape: "square",
    size: 16,
    color: MORE_COLOR,
    text: label,
    textVerticalShift: 1,
    textTruncate: false,
  },
};

const edgeStyle = {
  dashed: (edge) => ["context", "more"].includes(edge.getData()?.kind),
  markerEnd: (edge) =>
    edge.getData()?.kind === "derived" ? "arrow" : undefined,
  strokeWidth: (edge) => (edge.getData()?.kind === "derived" ? 2 : 1),
  opacity: (edge) => (edge.getData()?.kind === "derived" ? 0.85 : 0.5),
};

function sourceLabel(source) {
  if (!source) return "";
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.name || source.type;
}

function line(text, className = "") {
  const div = document.createElement("div");
  div.className = `small ${className}`;
  div.textContent = text;
  return div;
}

// Hover card: what each node is, beyond its (shortened) label.
const tooltip = {
  title: (node) => {
    const d = node.getData() || {};
    if (d.kind === "event") return d.event?.info || d.uuid;
    return d.label;
  },
  subtitle: (node) => {
    const d = node.getData() || {};
    if (d.kind === "event") return `event ${d.uuid}`;
    if (d.kind === "object") return `object ${d.uuid}`;
    if (d.kind === "more") return "not drawn";
    return d.type;
  },
  body: (node) => {
    const d = node.getData() || {};
    const body = document.createElement("div");
    if (d.attribute) {
      const a = d.attribute;
      body.append(
        line(
          [a.category, a.object_relation && `as ${a.object_relation}`]
            .filter(Boolean)
            .join(" · "),
        ),
        line(a.to_ids ? "to_ids" : "not for IDS", "text-muted"),
      );
      if (a.tags.length) body.append(line(a.tags.join(", "), "text-muted"));
      if (a.comment) body.append(line(a.comment, "fst-italic"));
    } else if (d.kind === "object") {
      const o = d.object;
      body.append(
        line(
          [o.meta_category, `${o.attribute_count + 1} attributes`]
            .filter(Boolean)
            .join(" · "),
        ),
      );
    } else if (d.kind === "event") {
      const e = d.event || {};
      body.append(
        line([e.date, sourceLabel(e.source)].filter(Boolean).join(" · ")),
      );
      if (e.org?.name) body.append(line(e.org.name, "text-muted"));
    } else if (d.kind === "more") {
      body.append(line("Only the newest events are drawn.", "text-muted"));
    }
    return body;
  },
};

const legendItems = computed(() => {
  const items = [
    { shape: "hexagon", color: INDICATOR_COLOR, label: "indicator" },
    { shape: "circle", color: ATTRIBUTE_COLOR, label: "attribute (to_ids)" },
    { shape: "circle", color: NON_IDS_COLOR, label: "attribute" },
  ];
  if (graph.value?.objects.length)
    items.push({ shape: "triangle", color: OBJECT_COLOR, label: "object" });
  items.push({ shape: "square", color: EVENT_COLOR, label: "event" });
  return items;
});

const caption = computed(() => {
  const g = graph.value;
  if (!g) return "";
  const parts = [
    `${g.attributes.length} ${g.attributes.length === 1 ? "attribute" : "attributes"}`,
    `${g.events.length} ${g.events.length === 1 ? "event" : "events"}`,
  ];
  if (g.objects.length)
    parts.push(
      `${g.objects.length} ${g.objects.length === 1 ? "object" : "objects"}`,
    );
  return parts.join(" · ");
});
</script>

<template>
  <div class="indicator-graph">
    <Spinner v-if="loading" />
    <div v-else-if="error" class="text-danger small">{{ error }}</div>
    <template v-else-if="graph">
      <p v-if="isEmpty" class="text-muted small mb-0">
        {{
          graph.indicator.deleted
            ? "This indicator is gone: no live attribute holds its value any more."
            : "No live attribute holds this value."
        }}
      </p>
      <template v-else>
        <div
          v-if="graph.objects.length && siblingCount"
          class="form-check form-switch small mb-2"
        >
          <input
            :id="`indicator-graph-siblings-${indicatorUuid}`"
            v-model="showSiblings"
            class="form-check-input"
            type="checkbox"
          />
          <label
            class="form-check-label"
            :for="`indicator-graph-siblings-${indicatorUuid}`"
          >
            Show the objects' other attributes ({{ siblingCount }})
          </label>
        </div>
        <!-- Rebuilt when the context is toggled: nodes added to a settled
             layout start at the origin and stay stranded there. -->
        <PivotickGraph
          :key="showSiblings ? 'with-context' : 'without-context'"
          :nodes="data.nodes"
          :edges="data.edges"
          :node-style-map="nodeStyleMap"
          :edge-style="edgeStyle"
          :tooltip="tooltip"
          :height="height"
          @navigate="router.push($event)"
        />
        <GraphLegend class="mt-2" :items="legendItems" />
        <p class="graph-caption mb-0 mt-1">
          {{ caption }} &middot; click a node to open it
          <template v-if="graph.omitted_events">
            &middot; {{ graph.omitted_events }} older
            {{ graph.omitted_events === 1 ? "event" : "events" }} not drawn
          </template>
          <template v-if="graph.truncated">
            &middot; too many attributes to read them all
          </template>
        </p>
      </template>
    </template>
  </div>
</template>

<style scoped>
.graph-caption {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}
</style>
