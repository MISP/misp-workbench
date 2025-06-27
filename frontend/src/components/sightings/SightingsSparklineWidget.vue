<script setup>
import { computed, watch, ref } from "vue";
import { storeToRefs } from "pinia";
import Sparkline from "@/components/charts/Sparkline.vue";
import { useSightingsStore } from "@/stores";

const props = defineProps({
  value: {
    type: String,
    required: true,
  },
});

const sightingsStore = useSightingsStore();
const { sightings } = storeToRefs(sightingsStore);

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

watch(
  [() => props.value, selectedPeriod],
  ([value, period]) => {
    if (value) {
      sightingsStore.get_histogram({
        value,
        period,
        interval: interval.value,
      });
    }
  },
  { immediate: true },
);

const points = computed(() => {
  const buckets = sightings.value?.sightings_over_time?.buckets || [];
  return buckets.map((bucket) => bucket.doc_count);
});
</script>

<template>
  <div class="mt-2 card">
    <div class="card-header border-bottom">
      <h6 class="card-title">sightings activity</h6>
    </div>

    <div class="card-body">
      <Sparkline :points="points" />
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
