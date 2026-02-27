<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useHuntsStore } from "@/stores";
import Sparkline from "@/components/charts/Sparkline.vue";

const props = defineProps({
  huntId: { type: Number, required: true },
  lastRunAt: { type: String, default: null },
});

const huntsStore = useHuntsStore();
const history = ref([]);

function fetchHistory() {
  huntsStore.getHistory(props.huntId).then((h) => {
    if (h) history.value = h;
  });
}

onMounted(fetchHistory);
watch(() => props.lastRunAt, fetchHistory);

const counts = computed(() => history.value.map((e) => e.match_count));
</script>

<template>
  <div v-if="counts.length > 1" class="d-flex align-items-center gap-2">
    <div style="width: 96px; height: 28px; flex-shrink: 0">
      <Sparkline :points="counts" />
    </div>
  </div>
  <span v-else-if="counts.length <= 1" class="fw-bold">—</span>
</template>
