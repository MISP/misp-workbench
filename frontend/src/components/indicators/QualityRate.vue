<script setup>
// A share (0-1) as a percentage, tinted when it is worth a look.
const props = defineProps({
  value: { type: Number, default: 0 },
  // "high" is good (hit rate), "low" is good (false positives); "none"
  // for shares that are neither (overlap, decay).
  good: { type: String, default: "high" },
});

function tone() {
  if (props.good === "none") return "";
  if (props.good === "low") {
    if (props.value >= 0.1) return "text-danger";
    if (props.value >= 0.03) return "text-warning-emphasis";
    return "";
  }
  return props.value >= 0.1 ? "text-success" : "";
}
</script>

<template>
  <span :class="tone()" class="font-monospace"
    >{{ (props.value * 100).toFixed(props.value < 0.1 ? 1 : 0) }}%</span
  >
</template>
