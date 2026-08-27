<script setup>
import { computed } from "vue";

const props = defineProps({
  timestamp: {
    type: [Number, String],
    default: null,
  },
});

/**
 * Two shapes of timestamp reach this component. MISP entities carry unix epoch
 * seconds (`timestamp`, as a number or a numeric string), while the OpenSearch
 * documents also carry ISO 8601 (`@timestamp`) - correlations are read straight
 * from those. Multiplying an ISO string by 1000 gives NaN, which is what showed
 * up as "Invalid Date", so the shape is detected rather than assumed.
 *
 * Computed rather than resolved once at setup, so a card reused for a new result
 * does not keep the previous one's date.
 */
const formatted = computed(() => {
  const value = props.timestamp;

  if (value === null || value === undefined || value === "") {
    return "";
  }

  const epochSeconds = Number(value);
  const date = Number.isNaN(epochSeconds)
    ? new Date(value)
    : new Date(epochSeconds * 1000);

  // Anything unparseable is left blank rather than shown as "Invalid Date".
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString();
});
</script>

<template>
  <span>{{ formatted }}</span>
</template>
