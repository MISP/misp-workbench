<script setup>
import { computed } from "vue";

const props = defineProps({
  eventTimestamp: { type: Number, required: true },
  retentionConfig: { type: Object, default: null },
  tags: { type: Array, default: () => [] },
});

const expiresInDays = computed(() => {
  if (!props.retentionConfig?.enabled) return null;

  const exemptTags = props.retentionConfig.exempt_tags || [];
  if (props.tags?.some((t) => exemptTags.includes(t.name))) return null;

  const now = Math.floor(Date.now() / 1000);
  const expiresAt =
    props.eventTimestamp + props.retentionConfig.period_days * 86400;
  return Math.ceil((expiresAt - now) / 86400);
});

const showBadge = computed(() => {
  if (expiresInDays.value === null) return false;
  return expiresInDays.value <= (props.retentionConfig?.warning_days ?? 30);
});
</script>

<template>
  <span v-if="showBadge">
    <span v-if="expiresInDays <= 0" class="badge bg-danger">expired</span>
    <span v-else class="badge bg-warning text-dark"
      >expires in {{ expiresInDays }}d</span
    >
  </span>
</template>
