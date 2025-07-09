<script setup>
import { computed, watch, ref } from "vue";
import { storeToRefs } from "pinia";
import { useSightingsStore } from "@/stores";

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
});

const sightingsStore = useSightingsStore();
const { stats } = storeToRefs(sightingsStore);

const selectedPeriod = ref("7d");

const interval = computed(() => {
  switch (selectedPeriod.value) {
    case "1d":
      return "1h";
    case "7d":
      return "1h";
    case "30d":
      return "1d";
    default:
      return "1h";
  }
});

const change = computed(() => {
  return stats.value.total - stats.value.previous_total;
});

const badgeColor = computed(() => {
  if (change.value >= 100) return "bg-danger";
  if (change.value >= 10) return "bg-warning";
  if (change.value > 0) return "bg-info";
  return "bg-secondary";
});

watch(
  [() => props.value, selectedPeriod],
  ([value, period]) => {
    if (value) {
      sightingsStore.getStats({
        value,
        period,
        interval: interval.value,
      });
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="mt-2 card">
    <div class="card-header border-bottom">
      <h6 class="card-title">sightings stats</h6>
    </div>

    <div
      class="card-body d-flex justify-content-between align-items-center p-3 shadow-sm rounded"
    >
      <div>
        <p class="text-muted mb-1 small">Total</p>
        <h2 class="mb-0 fw-bold">{{ stats.total || 0 }}</h2>
      </div>
      <span
        class="badge text-white d-flex align-items-center px-3 py-2 fs-6 rounded-pill shadow-sm"
        :class="badgeColor"
      >
        <font-awesome-icon icon="fa-solid fa-up-long" class="me-1" />
        <span class="fw-semibold">{{ change || 0 }}</span>
      </span>
    </div>

    <div
      class="card-footer text-muted d-flex justify-content-between align-items-center"
    >
      <small class="text-muted fst-italic">Time range:</small>
      <div class="btn-group btn-group-sm" role="group">
        <button
          type="button"
          class="btn btn-outline-secondary"
          :class="{ active: selectedPeriod === '1d' }"
          @click="selectedPeriod = '1d'"
        >
          1d
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :class="{ active: selectedPeriod === '7d' }"
          @click="selectedPeriod = '7d'"
        >
          7d
        </button>
        <button
          type="button"
          class="btn btn-outline-secondary"
          :class="{ active: selectedPeriod === '30d' }"
          @click="selectedPeriod = '30d'"
        >
          30d
        </button>
      </div>
    </div>
  </div>
</template>
