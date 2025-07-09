<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
const props = defineProps({
  points: {
    type: Array,
    required: true,
  },
});

const stroke = 3;
const width = ref(240); // Default, will auto-resize
const height = 96;

const shape = computed(() => {
  const h = height - stroke * 2;
  const data = props.points || [];
  const coordinates = [];

  if (data.length === 0) {
    return `M 0 ${stroke} L ${width.value} ${stroke}`;
  }

  const highestPoint = Math.max(...data) || 1; // Avoid divide-by-zero
  const totalPoints = data.length - 1 || 1;

  data.forEach((item, index) => {
    const x = (index / totalPoints) * width.value + stroke;
    const y = h - (item / highestPoint) * h + stroke;
    coordinates.push({ x, y });
  });

  return coordinates
    .map((p, i) => (i === 0 ? `M${p.x} ${p.y}` : `L${p.x} ${p.y}`))
    .join(" ");
});

const fillEndPath = computed(() => {
  return `V ${height} L 4 ${height} Z`;
});

let resizeObserver;

const container = ref(null);

const observeResize = () => {
  if (!container.value) return;

  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (entry.contentRect) {
        width.value = entry.contentRect.width;
      }
    }
  });
  resizeObserver.observe(container.value);
};
onMounted(() => {
  observeResize();
});

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
  }
});
</script>

<style scoped>
.sparkline {
  width: 100%;
  height: 100%;
  display: block;
}
</style>

<template>
  <div ref="container" style="width: 100%; height: 100%">
    <svg
      class="sparkline"
      width="100%"
      height="100%"
      :viewBox="`0 0 ${width} ${height}`"
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        :d="shape"
        fill="none"
        stroke="#007bff"
        :stroke-width="stroke"
        stroke-linecap="round"
      />
      <path :d="fillEndPath" fill="#007bff" opacity=".1" />
    </svg>
  </div>
</template>
