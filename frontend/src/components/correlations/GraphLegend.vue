<script setup>
/**
 * Key for a graph: what each shape means, and which colour belongs to which
 * attribute type. The swatches are handed the same colours the nodes are drawn
 * with, so the two cannot drift apart.
 */
defineProps({
  /** `[{ shape, color, label }]` — shape is hexagon, circle, square or dashed. */
  items: {
    type: Array,
    required: true,
  },
  /** `[{ type, color }]` for the colour-by-type key. */
  types: {
    type: Array,
    default: () => [],
  },
  /** Types left out of the key, reported rather than dropped silently. */
  omittedTypes: {
    type: Number,
    default: 0,
  },
});

const HEXAGON_POINTS = "6,0.5 10.8,3.25 10.8,8.75 6,11.5 1.2,8.75 1.2,3.25";
</script>

<template>
  <div class="graph-legend d-flex flex-wrap align-items-center gap-3">
    <span v-for="item in items" :key="item.label" class="legend-item">
      <svg viewBox="0 0 12 12" aria-hidden="true">
        <polygon
          v-if="item.shape === 'hexagon'"
          :points="HEXAGON_POINTS"
          :fill="item.color"
        />
        <rect
          v-else-if="item.shape === 'square'"
          x="1"
          y="1"
          width="10"
          height="10"
          :fill="item.color"
        />
        <line
          v-else-if="item.shape === 'dashed'"
          x1="0"
          y1="6"
          x2="12"
          y2="6"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-dasharray="3 2"
        />
        <line
          v-else-if="item.shape === 'line'"
          x1="0"
          y1="6"
          x2="12"
          y2="6"
          stroke="currentColor"
          stroke-width="1.5"
        />
        <circle v-else cx="6" cy="6" r="5" :fill="item.color" />
      </svg>
      {{ item.label }}
    </span>

    <span
      v-if="types.length > 1"
      class="legend-types d-flex flex-wrap align-items-center gap-2"
    >
      <span class="legend-types__label">types</span>
      <span
        v-for="entry in types"
        :key="entry.type"
        class="legend-item"
        :title="`attribute type ${entry.type}`"
      >
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <circle cx="6" cy="6" r="5" :fill="entry.color" />
        </svg>
        {{ entry.type }}
      </span>
      <span v-if="omittedTypes" class="legend-item">
        +{{ omittedTypes }} more
      </span>
    </span>
  </div>
</template>

<style scoped>
.graph-legend {
  font-size: 0.6875rem;
  color: var(--bs-secondary-color);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  white-space: nowrap;
}

.legend-item svg {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
}

/* The attribute types are a second key, so they are labelled as one rather
   than divided off with a rule that disappears once the row wraps. */
.legend-types__label {
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
