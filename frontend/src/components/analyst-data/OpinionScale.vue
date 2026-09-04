<script setup>
import { computed } from "vue";

const props = defineProps({
  opinion: { type: Number, required: true },
});

// MISP scores opinions 0-100. The bands mirror how it labels them, so the
// number is readable without having to remember the scale.
const band = computed(() => {
  const value = props.opinion;
  if (value <= 20) return { label: "Strongly disagree", variant: "danger" };
  if (value <= 40) return { label: "Disagree", variant: "warning" };
  if (value <= 60) return { label: "Neutral", variant: "secondary" };
  if (value <= 80) return { label: "Agree", variant: "info" };
  return { label: "Strongly agree", variant: "success" };
});
</script>

<template>
  <span class="d-inline-flex align-items-center gap-2">
    <span class="badge" :class="`text-bg-${band.variant}`">
      {{ opinion }}/100
    </span>
    <span class="text-body-secondary small">{{ band.label }}</span>
  </span>
</template>
