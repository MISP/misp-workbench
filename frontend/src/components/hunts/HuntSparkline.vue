<script setup>
import { ref, computed, onMounted } from "vue";
import { useHuntsStore } from "@/stores";
import Sparkline from "@/components/charts/Sparkline.vue";

const props = defineProps({ huntId: { type: Number, required: true } });

const huntsStore = useHuntsStore();
const history = ref([]);

onMounted(() => {
  huntsStore.getHistory(props.huntId).then((h) => {
    if (h) history.value = h;
  });
});

const counts = computed(() => history.value.map((e) => e.match_count));
const lastCount = computed(() =>
  history.value.length
    ? history.value[history.value.length - 1].match_count
    : null,
);
</script>

<template>
  <div v-if="counts.length > 1" class="d-flex align-items-center gap-2">
    <div style="width: 96px; height: 28px; flex-shrink: 0">
      <Sparkline :points="counts" />
    </div>
  </div>
  <span v-else-if="counts.length === 1" class="fw-bold">{{ lastCount }}</span>
  <span v-else class="text-muted">—</span>
</template>
