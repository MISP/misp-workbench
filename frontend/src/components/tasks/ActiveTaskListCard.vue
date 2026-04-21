<script setup>
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps({
  activeTasks: Object,
  cardId: {
    type: String,
    default: () => Math.random().toString(36).substring(2, 8),
  },
});

const taskList = computed(() => {
  return Object.values(props.activeTasks || {}).sort((a, b) => {
    // STARTED tasks first (by most recent), then RESERVED.
    if (a.state !== b.state) return a.state === "STARTED" ? -1 : 1;
    return (b.started || 0) - (a.started || 0);
  });
});

const runningCount = computed(
  () => taskList.value.filter((t) => t.state === "STARTED").length,
);
const reservedCount = computed(
  () => taskList.value.filter((t) => t.state === "RESERVED").length,
);

function formatTime(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function elapsed(ts) {
  if (!ts) return "—";
  const secs = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m ${rem}s`;
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-start">
      <h5 class="mb-0">Running Tasks</h5>
      <span class="badge ms-2 bg-primary">
        <FontAwesomeIcon
          v-if="runningCount > 0"
          :icon="faSpinner"
          spin
          class="me-1"
        />
        running: {{ runningCount }}
      </span>
      <span v-if="reservedCount > 0" class="badge ms-2 bg-secondary">
        queued: {{ reservedCount }}
      </span>
    </div>
    <div class="card-body">
      <div v-if="taskList.length === 0" class="text-muted">
        No tasks currently running.
      </div>
      <div v-else class="accordion" :id="'activeTaskAccordion-' + cardId">
        <div v-for="task in taskList" :key="task.uuid" class="accordion-item">
          <h2 class="accordion-header" :id="'active-heading-' + task.uuid">
            <button
              class="accordion-button collapsed"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="'#active-collapse-' + task.uuid"
              aria-expanded="false"
              :aria-controls="'active-collapse-' + task.uuid"
            >
              {{ task.name }}
              <span
                v-if="task.state === 'STARTED'"
                class="ms-2 text-muted small"
              >
                (running for {{ elapsed(task.started) }})
              </span>
              <span v-else class="ms-2 text-muted small">(queued)</span>
            </button>
          </h2>
          <div
            :id="'active-collapse-' + task.uuid"
            class="accordion-collapse collapse"
            :aria-labelledby="'active-heading-' + task.uuid"
            :data-bs-parent="'#activeTaskAccordion-' + cardId"
          >
            <div class="accordion-body small">
              <ul class="list-group list-group-flush">
                <li class="list-group-item">
                  <strong>UUID:</strong> {{ task.uuid }}
                </li>
                <li class="list-group-item">
                  <strong>Worker:</strong> {{ task.worker }}
                </li>
                <li class="list-group-item">
                  <strong>Args:</strong> {{ task.args }}
                </li>
                <li class="list-group-item">
                  <strong>Kwargs:</strong> {{ task.kwargs }}
                </li>
                <li class="list-group-item">
                  <strong>Received:</strong> {{ formatTime(task.received) }}
                </li>
                <li class="list-group-item">
                  <strong>Started:</strong> {{ formatTime(task.started) }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
