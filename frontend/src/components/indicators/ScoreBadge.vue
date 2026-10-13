<script setup>
import { computed } from "vue";

// A consolidated indicator's confidence (0-100), with how it was reached in
// the tooltip. `decayedBelow` matches the scoring.decayed_below setting.
const props = defineProps({
  score: { type: Number, default: null },
  breakdown: { type: Array, default: () => [] },
  decayedBelow: { type: Number, default: 30 },
});

const variant = computed(() => {
  if (props.score >= 70) return "text-bg-success";
  if (props.score >= 50) return "text-bg-primary";
  if (props.score >= props.decayedBelow) return "text-bg-warning";
  return "text-bg-secondary";
});

const explanation = computed(() =>
  props.breakdown
    .map(
      (c) =>
        `${c.points >= 0 && c.factor !== "base" ? "+" : ""}${c.points} ${c.factor} (${c.detail})`,
    )
    .join("\n"),
);
</script>

<template>
  <span
    v-if="score !== null && score !== undefined"
    class="badge score-badge"
    :class="variant"
    :title="`Confidence ${score}/100\n${explanation}`"
    >{{ score }}</span
  >
</template>

<style scoped>
.score-badge {
  min-width: 2.2em;
  font-variant-numeric: tabular-nums;
}
</style>
