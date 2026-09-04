<script setup>
import { computed } from "vue";
import { ColorPaletteMapper } from "pivotick";
import GraphLegend from "@/components/correlations/GraphLegend.vue";
import PivotickGraph from "@/components/graph/PivotickGraph.vue";
import { correlationHelper } from "@/helpers";

const props = defineProps({
  attribute: {
    type: Object,
    required: true,
  },
  correlations: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["navigate"]);

// Past this many correlated attributes the picture stops being readable, so the
// strongest matches are drawn and the rest is reported rather than dropped
// silently.
const MAX_CORRELATED_ATTRIBUTES = 150;
const LABEL_LENGTH = 18;
// Attribute types spelled out in the legend before it starts costing more room
// than it gives back.
const MAX_LEGEND_TYPES = 8;
// Shared with the legend swatches so a shape always carries the same colour.
const SUBJECT_COLOR = "#0d6efd";
const EVENT_COLOR = "#6c757d";
const NEUTRAL_COLOR = "#adb5bd";

function truncate(value) {
  const text = String(value ?? "");

  return text.length > LABEL_LENGTH
    ? `${text.slice(0, LABEL_LENGTH - 1)}…`
    : text;
}

function shortUuid(uuid) {
  return String(uuid ?? "").slice(0, 8);
}

const correlated = computed(() =>
  correlationHelper.mergeCorrelatedAttributes(props.correlations),
);

const drawn = computed(() =>
  correlated.value.slice(0, MAX_CORRELATED_ATTRIBUTES),
);

const omitted = computed(() => correlated.value.length - drawn.value.length);

const subjectEventUuid = computed(
  () =>
    props.attribute.event_uuid ??
    props.correlations[0]?._source?.source_event_uuid ??
    null,
);

/**
 * The neighbourhood is drawn as attributes joined to the events holding them:
 * the subject in the middle, one node per correlated attribute, and an event
 * node per event. The force layout then pulls each event's attributes together,
 * which is the clustering the list view spells out group by group.
 */
const graphData = computed(() => {
  const subjectId = `attribute:${props.attribute.uuid}`;
  const nodes = [
    {
      id: subjectId,
      data: {
        kind: "subject",
        label: props.attribute.value,
        type: props.attribute.type,
        route: `/attributes/${props.attribute.uuid}`,
      },
    },
  ];
  const edges = [];
  const eventIds = new Set();

  const addEvent = (eventUuid) => {
    if (!eventUuid || eventIds.has(eventUuid)) {
      return `event:${eventUuid}`;
    }

    eventIds.add(eventUuid);
    nodes.push({
      id: `event:${eventUuid}`,
      data: {
        kind: "event",
        label: shortUuid(eventUuid),
        uuid: eventUuid,
        route: `/events/${eventUuid}`,
      },
    });

    return `event:${eventUuid}`;
  };

  if (subjectEventUuid.value) {
    edges.push({
      from: subjectId,
      to: addEvent(subjectEventUuid.value),
      data: { kind: "membership" },
    });
  }

  for (const attribute of drawn.value) {
    const id = `attribute:${attribute.uuid}`;
    const approximate = attribute.matches.some((match) =>
      correlationHelper.isApproximateMatch(match.type),
    );

    nodes.push({
      id,
      data: {
        kind: "attribute",
        label: attribute.value,
        type: attribute.type,
        route: `/attributes/${attribute.uuid}`,
      },
    });

    edges.push({
      from: subjectId,
      to: id,
      // No edge label: the library renders data.label on the edge, and a match
      // type on every spoke buries the values. Approximate matches are dashed
      // instead, and the list view spells the match types out.
      data: {
        kind: "correlation",
        approximate,
      },
    });

    if (attribute.eventUuid) {
      edges.push({
        from: id,
        to: addEvent(attribute.eventUuid),
        data: { kind: "membership" },
      });
    }
  }

  return { nodes, edges };
});

// Counted off the drawn nodes rather than the correlations, so the caption
// agrees with the picture: the subject's own event is drawn as well.
const eventCount = computed(
  () =>
    graphData.value.nodes.filter((node) => node.data.kind === "event").length,
);

const types = computed(() =>
  [...new Set(drawn.value.map((attribute) => attribute.type))].sort(),
);

/**
 * Colours are claimed per attribute type in a stable order, so a type keeps its
 * colour between renders instead of shuffling with the result order. The graph
 * and the legend read from this same mapper, so the swatches cannot drift from
 * the nodes.
 */
const palette = computed(() => {
  const mapper = new ColorPaletteMapper();
  types.value.forEach((type) => mapper.getColor(type));

  return mapper;
});

const typeLegend = computed(() =>
  types.value.slice(0, MAX_LEGEND_TYPES).map((type) => ({
    type,
    color: palette.value.getColor(type),
  })),
);

const omittedTypes = computed(
  () => types.value.length - typeLegend.value.length,
);

const hasApproximateMatch = computed(() =>
  drawn.value.some((attribute) =>
    attribute.matches.some((match) =>
      correlationHelper.isApproximateMatch(match.type),
    ),
  ),
);

const legendItems = computed(() => {
  const items = [
    { shape: "hexagon", color: SUBJECT_COLOR, label: "this attribute" },
    { shape: "circle", color: NEUTRAL_COLOR, label: "correlated attribute" },
    { shape: "square", color: EVENT_COLOR, label: "event" },
  ];

  if (hasApproximateMatch.value) {
    items.push({ shape: "dashed", label: "approximate match" });
  }

  return items;
});

const nodeStyleMap = computed(() => ({
  subject: {
    shape: "hexagon",
    size: 26,
    color: SUBJECT_COLOR,
    text: (node) => truncate(node.getData()?.label),
    textVerticalShift: -1,
  },
  // The label budget is derived from the node size, so these are sized for
  // their text as much as for their weight in the picture.
  attribute: {
    shape: "circle",
    size: 20,
    color: (node) => palette.value.getColor(node.getData()?.type),
    text: (node) => truncate(node.getData()?.label),
    textVerticalShift: -1,
  },
  event: {
    shape: "square",
    size: 18,
    color: EVENT_COLOR,
    text: (node) => node.getData()?.label,
    textVerticalShift: 1,
  },
}));

const edgeStyle = {
  // An inexact match is dashed, the same signal the list view gives it.
  dashed: (edge) => edge.getData()?.approximate === true,
  markerEnd: (edge) =>
    edge.getData()?.kind === "membership" ? undefined : "arrow",
  // Correlations are the subject of the picture; the edges tying an attribute
  // to its event are context, so they stay thin and quiet without
  // disappearing on a dark canvas. Function valued fields, not styleCb: the
  // drawer only consults styleCb for a style set on an individual edge.
  strokeWidth: (edge) => (edge.getData()?.kind === "membership" ? 1 : 2),
  opacity: (edge) => (edge.getData()?.kind === "membership" ? 0.45 : 0.85),
};

// Node labels are shortened to fit, so hovering carries the full value.
const tooltip = {
  title: (node) => node.getData()?.label,
  subtitle: (node) =>
    node.getData()?.kind === "event"
      ? `event ${node.getData()?.uuid ?? ""}`
      : node.getData()?.type,
};
</script>

<template>
  <div class="correlation-graph">
    <PivotickGraph
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :node-style-map="nodeStyleMap"
      :edge-style="edgeStyle"
      :tooltip="tooltip"
      @navigate="emit('navigate', $event)"
    />

    <GraphLegend
      class="mt-2"
      :items="legendItems"
      :types="typeLegend"
      :omitted-types="omittedTypes"
    />

    <p class="graph-caption mb-0 mt-2">
      {{ drawn.length }}
      {{ drawn.length === 1 ? "attribute" : "attributes" }} in {{ eventCount }}
      {{ eventCount === 1 ? "event" : "events" }} &middot; click a node to open
      it
      <template v-if="omitted">
        &middot; {{ omitted }} weaker
        {{ omitted === 1 ? "correlation" : "correlations" }} not drawn
      </template>
    </p>
  </div>
</template>

<style scoped>
.graph-caption {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}
</style>
