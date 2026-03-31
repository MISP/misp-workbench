<script setup>
import { ref, computed } from "vue";
import { Bar } from "vue-chartjs";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
  TimeScale,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
  TimeScale,
);

const emit = defineEmits(["filter-day"]);

const props = defineProps({
  eventBuckets: {
    type: Array,
    default: () => [],
  },
  attributeBuckets: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

function formatDate(keyAsString) {
  const d = new Date(keyAsString);
  return d.toISOString().slice(0, 10);
}

const chartData = computed(() => {
  const allDates = new Set([
    ...props.eventBuckets.map((b) => formatDate(b.key_as_string)),
    ...props.attributeBuckets.map((b) => formatDate(b.key_as_string)),
  ]);
  const labels = Array.from(allDates).sort();

  const eventMap = Object.fromEntries(
    props.eventBuckets.map((b) => [formatDate(b.key_as_string), b.doc_count]),
  );
  const attributeMap = Object.fromEntries(
    props.attributeBuckets.map((b) => [
      formatDate(b.key_as_string),
      b.doc_count,
    ]),
  );

  const datasets = [];
  if (showEvents.value) {
    datasets.push({
      label: "Events",
      data: labels.map((d) => eventMap[d] ?? 0),
      backgroundColor: "rgba(13, 110, 253, 0.7)",
      borderColor: "rgba(13, 110, 253, 0.9)",
      borderWidth: 1,
      barPercentage: 0.9,
      categoryPercentage: 1.0,
      stack: "timeline",
    });
  }
  if (showAttributes.value) {
    datasets.push({
      label: "Attributes",
      data: labels.map((d) => attributeMap[d] ?? 0),
      backgroundColor: "rgba(25, 135, 84, 0.7)",
      borderColor: "rgba(25, 135, 84, 0.9)",
      borderWidth: 1,
      barPercentage: 0.9,
      categoryPercentage: 1.0,
      stack: "timeline",
    });
  }

  return { labels, datasets };
});

const chartOptions = {
  onClick(event, elements, chart) {
    if (!elements.length) return;
    const date = chart.data.labels[elements[0].index];
    emit("filter-day", date);
  },
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: {
      position: "top",
      labels: {
        boxWidth: 12,
        padding: 10,
        font: { size: 11 },
      },
    },
    tooltip: {
      mode: "index",
      intersect: false,
    },
  },
  scales: {
    x: {
      stacked: true,
      ticks: {
        maxRotation: 45,
        autoSkip: true,
        maxTicksLimit: 20,
        font: { size: 10 },
      },
      grid: { display: false },
    },
    y: {
      stacked: true,
      beginAtZero: true,
      ticks: {
        precision: 0,
        font: { size: 10 },
      },
    },
  },
};

const showEvents = ref(true);
const showAttributes = ref(true);

const hasData = computed(
  () => props.eventBuckets.length > 0 || props.attributeBuckets.length > 0,
);
</script>

<template>
  <div class="explore-timeline">
    <div
      v-if="loading"
      class="d-flex align-items-center justify-content-center"
      style="height: 120px"
    >
      <div
        class="spinner-border spinner-border-sm text-secondary me-2"
        role="status"
      ></div>
      <span class="text-muted small">Loading timeline…</span>
    </div>
    <div v-else-if="hasData">
      <div class="d-flex justify-content-end mb-1">
        <div class="btn-group btn-group-sm">
          <button
            class="btn btn-outline-primary"
            :class="{ active: showEvents }"
            @click="showEvents = !showEvents"
          >
            Events
          </button>
          <button
            class="btn btn-outline-success"
            :class="{ active: showAttributes }"
            @click="showAttributes = !showAttributes"
          >
            Attributes
          </button>
        </div>
      </div>
      <div style="height: 140px; cursor: pointer">
        <Bar :data="chartData" :options="chartOptions" />
      </div>
    </div>
  </div>
</template>
