<script setup>
/**
 * The correlation network, read from the correlation documents themselves: the
 * stats endpoint only returns per entity counts, so the pairs have to come from
 * the documents. Two ways to look at the same sample - which events are tied
 * together by the indicators they share, or which indicators correlate with
 * which.
 */
import { computed, onMounted, ref } from "vue";
import { ColorPaletteMapper } from "pivotick";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faCircleInfo, faSitemap } from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import GraphLegend from "@/components/correlations/GraphLegend.vue";
import PivotickGraph from "@/components/correlations/PivotickGraph.vue";
import { correlationHelper, tagHelper } from "@/helpers";
import { useCorrelationsStore, useEventsStore } from "@/stores";

const emit = defineEmits(["navigate"]);

// The search endpoint caps a page at 100 documents; three of them is a big
// enough sample to show the shape of the network without stalling the view.
const SAMPLE_PAGES = 3;
const SAMPLE_PAGE_SIZE = 100;
// Past this many nodes the picture stops being readable, so the busiest are
// drawn and the rest is reported rather than dropped silently.
const MAX_NODES = 150;
const MAX_LEGEND_TYPES = 8;
const MAX_TOOLTIP_TAGS = 6;
// How far a newly expanded neighbour starts from the node it came from.
const SEED_RADIUS = 60;
const LABEL_LENGTH = 18;
const EVENT_COLOR = "#6c757d";
const NEUTRAL_COLOR = "#adb5bd";

const correlationsStore = useCorrelationsStore();
const eventsStore = useEventsStore();

// What an event is called and how it is tagged, read the first time a node is
// hovered. Plain Maps, not refs: the tooltip is handed a DOM element by the
// library, so it is repainted directly rather than through rendering.
const eventDetails = new Map();
const loadingDetails = new Set();
const tooltipBodies = new Map();

const documents = ref([]);
const total = ref(0);
const loading = ref(true);
const error = ref(null);
const mode = ref("events");

// Events walked outward from, the neighbours that walk brought in, and the
// connections between them. Kept apart from the sampled base network so an
// expansion is never culled by the cap that trims the sample.
const expanded = ref(new Set());
const expanding = ref(new Set());
const discoveredEvents = ref(new Map());
const discoveredLinks = ref(new Map());
const budgetReached = ref(false);

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

function truncate(value) {
  const text = String(value ?? "");

  return text.length > LABEL_LENGTH
    ? `${text.slice(0, LABEL_LENGTH - 1)}…`
    : text;
}

/** Keep the busiest nodes, and only the links between the ones kept. */
function capNetwork(nodes, links) {
  if (nodes.length <= MAX_NODES) {
    return { nodes, links, omitted: 0 };
  }

  const kept = nodes.slice(0, MAX_NODES);
  const keptIds = new Set(kept.map((node) => node.id));

  return {
    nodes: kept,
    links: links.filter(
      (link) => keptIds.has(link.from) && keptIds.has(link.to),
    ),
    omitted: nodes.length - kept.length,
  };
}

/**
 * Correlations are stored once per direction, so a pair shows up twice. Every
 * weight counts distinct pairs of attributes, which keeps a mutual correlation
 * from counting double.
 */
const eventNetwork = computed(() => {
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
      link = { from: left, to: right, weight: new Set() };
      links.set(`${left}|${right}`, link);
    }
    link.weight.add(attributePair);

    for (const uuid of [left, right]) {
      let event = events.get(uuid);
      if (!event) {
        event = { uuid, weight: new Set() };
        events.set(uuid, event);
      }
      event.weight.add(attributePair);
    }
  }

  const nodes = [...events.values()]
    .sort((a, b) => b.weight.size - a.weight.size)
    .map((event) => ({
      id: event.uuid,
      data: {
        kind: "event",
        label: shortUuid(event.uuid),
        uuid: event.uuid,
        weight: event.weight.size,
        route: `/events/${event.uuid}`,
      },
    }));

  const edges = [...links.values()].map((link) => ({
    from: link.from,
    to: link.to,
    data: { weight: link.weight.size },
  }));

  return mergeExpansion(capNetwork(nodes, edges));
});

/**
 * Fold what expanding nodes brought in on top of the sampled network. The
 * sample is capped, the expansion is not: a node the reader asked for has to
 * stay on screen, so the budget is enforced when expanding instead.
 */
function mergeExpansion(base) {
  if (!discoveredEvents.value.size && !discoveredLinks.value.size) {
    return base;
  }

  const nodes = [...base.nodes];
  const seen = new Set(nodes.map((node) => node.id));

  for (const [uuid, discovered] of discoveredEvents.value) {
    if (seen.has(uuid)) {
      continue;
    }

    seen.add(uuid);
    nodes.push({
      id: uuid,
      // Seeded next to the event it was found from, so an expansion grows out
      // of the node that was clicked rather than arriving from off screen.
      x: discovered.x,
      y: discovered.y,
      data: {
        kind: "event",
        label: shortUuid(uuid),
        uuid,
        weight: discovered.weight,
        route: `/events/${uuid}`,
      },
    });
  }

  const edges = [...base.links];
  const edgeKeys = new Set(
    edges.map((edge) => [edge.from, edge.to].sort().join("|")),
  );

  for (const [key, link] of discoveredLinks.value) {
    if (edgeKeys.has(key) || !seen.has(link.from) || !seen.has(link.to)) {
      continue;
    }

    edgeKeys.add(key);
    edges.push({ from: link.from, to: link.to, data: { weight: link.weight } });
  }

  return { nodes, links: edges, omitted: base.omitted };
}

/**
 * Walk one step out from an event: the events it shares indicators with, added
 * to the picture rather than replacing it.
 *
 * The endpoint returns the strongest neighbours only, which doubles as the
 * per-node fan-out cap. Two more guards matter here: an event is only walked
 * once, and the whole graph stops growing at MAX_NODES - a single popular value
 * can correlate with a thousand others, and without a budget one expansion
 * would bury everything already on screen.
 */
/** A spot just off the expanded node, so its neighbours appear beside it. */
function seedPosition(node) {
  if (typeof node?.x !== "number" || typeof node?.y !== "number") {
    return {};
  }

  const angle = Math.random() * Math.PI * 2;

  return {
    x: node.x + Math.cos(angle) * SEED_RADIUS,
    y: node.y + Math.sin(angle) * SEED_RADIUS,
  };
}

async function expand(node) {
  const uuid = node?.uuid;

  if (
    mode.value !== "events" ||
    !uuid ||
    expanded.value.has(uuid) ||
    expanding.value.has(uuid)
  ) {
    return;
  }

  if (network.value.nodes.length >= MAX_NODES) {
    budgetReached.value = true;
    return;
  }

  expanding.value = new Set(expanding.value).add(uuid);

  try {
    const neighbours = await correlationsStore.eventNeighbours(uuid);
    const events = new Map(discoveredEvents.value);
    const links = new Map(discoveredLinks.value);
    let room = MAX_NODES - network.value.nodes.length;

    for (const bucket of neighbours || []) {
      const known =
        events.has(bucket.key) ||
        network.value.nodes.some((existing) => existing.id === bucket.key);

      if (!known) {
        if (room <= 0) {
          budgetReached.value = true;
          break;
        }

        room -= 1;
        // The bucket count is what this pair shares. A newly discovered event
        // has no total of its own yet, so its own edge stands in for its size.
        events.set(bucket.key, {
          uuid: bucket.key,
          weight: bucket.doc_count,
          ...seedPosition(node),
        });
      }

      links.set([uuid, bucket.key].sort().join("|"), {
        from: uuid,
        to: bucket.key,
        weight: bucket.doc_count,
      });
    }

    discoveredEvents.value = events;
    discoveredLinks.value = links;
    expanded.value = new Set(expanded.value).add(uuid);
  } catch (caught) {
    error.value = caught;
  } finally {
    const pending = new Set(expanding.value);
    pending.delete(uuid);
    expanding.value = pending;
  }
}

/**
 * The attribute view. A correlation document names the target's type and value
 * but only the source's type; since every pair is stored in both directions the
 * reverse document supplies the missing value, and a short uuid stands in when
 * it was not part of the sample.
 */
const attributeNetwork = computed(() => {
  const attributes = new Map();
  const links = new Map();

  const upsert = (uuid, type, value) => {
    if (!uuid) {
      return null;
    }

    let attribute = attributes.get(uuid);
    if (!attribute) {
      attribute = { uuid, type, value, peers: new Set() };
      attributes.set(uuid, attribute);
    }

    attribute.type = attribute.type ?? type;
    attribute.value = attribute.value ?? value;

    return attribute;
  };

  for (const document of documents.value) {
    const source = document._source;

    upsert(
      source.source_attribute_uuid,
      source.source_attribute_type,
      undefined,
    );
    upsert(
      source.target_attribute_uuid,
      source.target_attribute_type,
      source.target_attribute_value,
    );
  }

  for (const document of documents.value) {
    const source = document._source;
    const from = source.source_attribute_uuid;
    const to = source.target_attribute_uuid;

    if (!from || !to || from === to) {
      continue;
    }

    const [left, right] = [from, to].sort();
    let link = links.get(`${left}|${right}`);
    if (!link) {
      link = { from: left, to: right, matchTypes: new Set() };
      links.set(`${left}|${right}`, link);
    }
    link.matchTypes.add(source.match_type);

    attributes.get(left)?.peers.add(right);
    attributes.get(right)?.peers.add(left);
  }

  const nodes = [...attributes.values()]
    .filter((attribute) => attribute.peers.size)
    .sort((a, b) => b.peers.size - a.peers.size)
    .map((attribute) => ({
      id: attribute.uuid,
      data: {
        kind: "attribute",
        label: attribute.value ?? shortUuid(attribute.uuid),
        value: attribute.value,
        type: attribute.type,
        weight: attribute.peers.size,
        route: `/attributes/${attribute.uuid}`,
      },
    }));

  const edges = [...links.values()].map((link) => ({
    from: link.from,
    to: link.to,
    data: {
      weight: link.matchTypes.size,
      approximate: [...link.matchTypes].some((matchType) =>
        correlationHelper.isApproximateMatch(matchType),
      ),
    },
  }));

  return capNetwork(nodes, edges);
});

const network = computed(() =>
  mode.value === "events" ? eventNetwork.value : attributeNetwork.value,
);

const types = computed(() =>
  [
    ...new Set(
      attributeNetwork.value.nodes
        .map((node) => node.data.type)
        .filter(Boolean),
    ),
  ].sort(),
);

// The graph and the legend read the same mapper, so a swatch cannot drift from
// the nodes it stands for.
const palette = computed(() => {
  const mapper = new ColorPaletteMapper();
  types.value.forEach((type) => mapper.getColor(type));

  return mapper;
});

const typeLegend = computed(() =>
  mode.value === "attributes"
    ? types.value.slice(0, MAX_LEGEND_TYPES).map((type) => ({
        type,
        color: palette.value.getColor(type),
      }))
    : [],
);

const omittedTypes = computed(() =>
  mode.value === "attributes"
    ? types.value.length - typeLegend.value.length
    : 0,
);

const hasApproximateMatch = computed(() =>
  network.value.links.some((link) => link.data?.approximate),
);

const sampled = computed(() => documents.value.length);

const nodeStyleMap = computed(() => ({
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
  attribute: {
    shape: "circle",
    size: (node) =>
      13 + Math.min(11, Math.sqrt(node.getData()?.weight ?? 1) * 3),
    color: (node) => palette.value.getColor(node.getData()?.type),
    text: (node) => truncate(node.getData()?.label),
    textVerticalShift: -1,
  },
}));

// A correlation network is sparsely linked - plenty of pairs share a value with
// each other and nothing else - and isolated components drift apart under the
// repulsion a denser graph wants. Softer charge plus a real centring pull for
// connected nodes keeps them in frame.
const simulation = {
  d3LinkDistance: 70,
  d3ManyBodyStrength: -220,
  d3GravityStrengthConnected: 0.06,
};

// Function valued fields, not styleCb: the drawer only consults styleCb for a
// style set on an individual edge, while these resolve per edge from the
// renderer defaults.
const edgeStyle = {
  strokeWidth: (edge) => 1 + Math.min(6, edge.getData()?.weight ?? 1),
  opacity: 0.75,
  dashed: (edge) => edge.getData()?.approximate === true,
};

const legendItems = computed(() => {
  if (mode.value === "events") {
    return [
      {
        shape: "square",
        color: EVENT_COLOR,
        label: "event · bigger shares more",
      },
      { shape: "line", label: "shared indicators · thicker shares more" },
    ];
  }

  const items = [
    {
      shape: "circle",
      color: NEUTRAL_COLOR,
      label: "attribute · bigger correlates more",
    },
    { shape: "line", label: "correlation" },
  ];

  if (hasApproximateMatch.value) {
    items.push({ shape: "dashed", label: "approximate match" });
  }

  return items;
});

function mutedLine(text) {
  const line = document.createElement("div");
  line.textContent = text;
  line.style.color = "var(--bs-secondary-color)";

  return line;
}

function tagChip(tag) {
  const chip = document.createElement("span");
  chip.textContent = tagHelper.getTag("", tag.name);
  chip.style.backgroundColor = tagHelper.getBackgroundColor(tag.colour);
  chip.style.color = tagHelper.getContrastColor(tag.colour);
  chip.style.borderRadius = "0.25rem";
  chip.style.padding = "0.05rem 0.35rem";
  chip.style.fontSize = "0.6875rem";
  chip.style.whiteSpace = "nowrap";

  return chip;
}

/**
 * Styled inline rather than through the stylesheet: these elements are built
 * imperatively for the library, so they carry no scope attribute and scoped
 * rules would not reach them.
 */
function paintEventDetails(element, uuid) {
  const details = eventDetails.get(uuid);

  element.replaceChildren();

  if (!details) {
    element.append(mutedLine("Loading event…"));
    return;
  }

  if (details.error) {
    element.append(mutedLine("Could not load this event"));
    return;
  }

  if (details.info) {
    const name = document.createElement("div");
    name.textContent = details.info;
    name.style.fontWeight = "600";
    name.className = "text-info text-break";
    name.style.marginBottom = details.tags.length ? "0.25rem" : "0";
    element.append(name);
  }

  if (details.tags.length) {
    const row = document.createElement("div");
    row.style.display = "flex";
    row.style.flexWrap = "wrap";
    row.style.gap = "0.2rem";

    for (const tag of details.tags.slice(0, MAX_TOOLTIP_TAGS)) {
      row.append(tagChip(tag));
    }

    if (details.tags.length > MAX_TOOLTIP_TAGS) {
      row.append(mutedLine(`+${details.tags.length - MAX_TOOLTIP_TAGS}`));
    }

    element.append(row);
  }

  if (!details.info && !details.tags.length) {
    element.append(mutedLine("No name or tags"));
  }
}

async function loadEventDetails(uuid) {
  if (eventDetails.has(uuid) || loadingDetails.has(uuid)) {
    return;
  }

  loadingDetails.add(uuid);

  try {
    const event = await eventsStore.summary(uuid);
    eventDetails.set(uuid, {
      info: event?.info ?? "",
      tags: event?.tags ?? [],
    });
  } catch {
    eventDetails.set(uuid, { error: true });
  } finally {
    loadingDetails.delete(uuid);

    // The library still holds the element it was given, so filling it in now
    // updates a tooltip that is already open.
    const element = tooltipBodies.get(uuid);
    if (element) {
      paintEventDetails(element, uuid);
    }
  }
}

function eventTooltipBody(node) {
  const uuid = node.getData()?.uuid;
  const element = document.createElement("div");
  element.style.marginTop = "0.35rem";
  element.style.fontSize = "0.75rem";

  if (!uuid) {
    return element;
  }

  tooltipBodies.set(uuid, element);
  paintEventDetails(element, uuid);
  loadEventDetails(uuid);

  return element;
}

const tooltip = computed(() =>
  mode.value === "events"
    ? {
        title: (node) => node.getData()?.uuid,
        subtitle: (node) => {
          const weight = node.getData()?.weight ?? 0;

          return `${weight} shared ${weight === 1 ? "indicator" : "indicators"}`;
        },
        body: eventTooltipBody,
      }
    : {
        title: (node) => node.getData()?.label,
        subtitle: (node) => {
          const weight = node.getData()?.weight ?? 0;

          return `${node.getData()?.type ?? "attribute"} · correlates with ${weight}`;
        },
      },
);
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

  <div v-else>
    <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
      <div
        class="btn-group btn-group-sm flex-shrink-0"
        role="group"
        aria-label="Network subject"
      >
        <button
          type="button"
          class="btn"
          :class="mode === 'events' ? 'btn-secondary' : 'btn-outline-secondary'"
          :aria-pressed="mode === 'events'"
          @click="mode = 'events'"
        >
          Events
        </button>
        <button
          type="button"
          class="btn"
          :class="
            mode === 'attributes' ? 'btn-secondary' : 'btn-outline-secondary'
          "
          :aria-pressed="mode === 'attributes'"
          @click="mode = 'attributes'"
        >
          Attributes
        </button>
      </div>

      <p class="graph-caption mb-0">
        <template v-if="mode === 'events'">
          Events tied together by the indicators they share
        </template>
        <template v-else>Indicators that correlate with each other</template>
      </p>
    </div>

    <div v-if="!network.nodes.length" class="empty text-center py-5">
      <FontAwesomeIcon :icon="faSitemap" class="empty__icon mb-3" />
      <p class="mb-1">
        {{
          mode === "events" ? "No connected events yet" : "No correlations yet"
        }}
      </p>
      <p class="text-body-secondary small mb-0">
        <template v-if="mode === 'events'">
          Correlations link events that share an indicator. None of the sampled
          correlations join two different events.
        </template>
        <template v-else>
          Nothing in the sampled correlations pairs two attributes.
        </template>
      </p>
    </div>

    <template v-else>
      <PivotickGraph
        :nodes="network.nodes"
        :edges="network.links"
        :node-style-map="nodeStyleMap"
        :edge-style="edgeStyle"
        :is-directed="false"
        :tooltip="tooltip"
        :simulation="simulation"
        :expandable="mode === 'events'"
        height="min(70vh, 34rem)"
        @navigate="emit('navigate', $event)"
        @expand="expand"
      />

      <GraphLegend
        class="mt-2"
        :items="legendItems"
        :types="typeLegend"
        :omitted-types="omittedTypes"
      />

      <p class="graph-hint mb-0 mt-2">
        <FontAwesomeIcon :icon="faCircleInfo" class="me-1" />
        <template v-if="mode === 'events'">
          <strong>Click</strong> an event to pull in the events it connects to.
          <strong>Double-click</strong> to open it. Drag to rearrange, scroll to
          zoom.
        </template>
        <template v-else>
          <strong>Click</strong> an attribute to open it. Drag to rearrange,
          scroll to zoom.
        </template>
      </p>

      <p class="graph-caption mb-0 mt-1">
        {{ network.nodes.length }}
        <template v-if="mode === 'events'">
          connected
          {{ network.nodes.length === 1 ? "event" : "events" }}
        </template>
        <template v-else>
          correlated
          {{ network.nodes.length === 1 ? "attribute" : "attributes" }}
        </template>
        &middot; {{ network.links.length }}
        {{ network.links.length === 1 ? "connection" : "connections" }}
        <template v-if="expanded.size">
          &middot; {{ expanded.size }}
          {{ expanded.size === 1 ? "event" : "events" }} expanded
        </template>
        <template v-if="expanding.size"> &middot; expanding… </template>
        <template v-if="budgetReached">
          <br />
          Stopped growing at {{ MAX_NODES }} nodes. Open an event to keep
          following it from there.
        </template>
        <template v-if="network.omitted">
          &middot; {{ network.omitted }} quieter
          {{ network.omitted === 1 ? "node" : "nodes" }} not drawn
        </template>
        <template v-if="total > sampled">
          <br />
          Built from the {{ sampled.toLocaleString() }} most recent of
          {{ total.toLocaleString() }} correlations.
        </template>
      </p>
    </template>
  </div>
</template>

<style scoped>
.graph-caption {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}

/* What the graph responds to, kept apart from what it currently contains. */
.graph-hint {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}

.graph-hint strong {
  font-weight: 600;
  color: var(--bs-body-color);
}

.empty__icon {
  font-size: 1.75rem;
  color: var(--bs-secondary-color);
  opacity: 0.6;
}
</style>
