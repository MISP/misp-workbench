<script setup>
import { ref, onMounted, onUnmounted } from "vue";
import { useTasksStore, useDiagnosticsStore } from "@/stores";
import WorkersCard from "@/components/diagnostics/WorkersCard.vue";
import OpenSearchCard from "@/components/diagnostics/OpenSearchCard.vue";
import RedisCard from "@/components/diagnostics/RedisCard.vue";
import PostgresCard from "@/components/diagnostics/PostgresCard.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faRotate } from "@fortawesome/free-solid-svg-icons";

const REFRESH_INTERVAL_MS = 30_000;

const tasksStore = useTasksStore();
const diagnosticsStore = useDiagnosticsStore();

const autoRefresh = ref(true);
const lastUpdated = ref(null);
let timer = null;

function refresh() {
  tasksStore.get_workers();
  diagnosticsStore.getOpensearch();
  diagnosticsStore.getRedis();
  diagnosticsStore.getPostgres();
  lastUpdated.value = new Date();
}

function startTimer() {
  timer = setInterval(refresh, REFRESH_INTERVAL_MS);
}

function stopTimer() {
  clearInterval(timer);
  timer = null;
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value;
  if (autoRefresh.value) {
    startTimer();
  } else {
    stopTimer();
  }
}

onMounted(() => {
  refresh();
  startTimer();
});

onUnmounted(() => {
  stopTimer();
});

function formatTime(date) {
  if (!date) return null;
  return date.toLocaleTimeString();
}
</script>

<template>
  <div class="container mt-4">
    <div class="card shadow">
      <!-- Global card header -->
      <div class="card-header d-flex align-items-center gap-3">
        <h5 class="mb-0 me-auto">Diagnostics</h5>

        <span v-if="lastUpdated" class="text-muted small">
          Updated at {{ formatTime(lastUpdated) }}
        </span>

        <button
          class="btn btn-sm btn-outline-secondary"
          title="Refresh now"
          @click="refresh"
        >
          <FontAwesomeIcon :icon="faRotate" />
        </button>

        <div
          class="form-check form-switch mb-0 d-flex align-items-center gap-2"
        >
          <input
            class="form-check-input"
            type="checkbox"
            id="autoRefreshToggle"
            :checked="autoRefresh"
            @change="toggleAutoRefresh"
          />
          <label class="form-check-label small" for="autoRefreshToggle">
            Auto-refresh (30s)
          </label>
        </div>
      </div>

      <!-- Cards -->
      <div class="card-body">
        <OpenSearchCard />
        <RedisCard />
        <PostgresCard />
        <WorkersCard />
      </div>
    </div>
  </div>
</template>
