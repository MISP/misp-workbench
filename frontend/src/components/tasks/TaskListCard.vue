<script setup>
import { ref } from "vue";
import { computed } from "vue";

const props = defineProps({
  tasks: Object,
  cardId: {
    type: String,
    default: () => Math.random().toString(36).substring(2, 8),
  },
  pageSize: {
    type: Number,
    default: 10,
  },
});

const currentPage = ref(1);

const totalPages = computed(() =>
  Math.ceil(Object.values(props.tasks).length / props.pageSize),
);

const sortedTasks = computed(() =>
  Object.values(props.tasks).sort((a, b) => b.timestamp - a.timestamp),
);

const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize;
  return sortedTasks.value.slice(start, start + props.pageSize);
});

const taskTotalCount = computed(() => Object.keys(props.tasks).length);
const taskTotalFailureCount = computed(
  () =>
    Object.values(props.tasks).filter((task) => task.state === "FAILURE")
      .length,
);
const taskTotalSuccessCount = computed(
  () =>
    Object.values(props.tasks).filter((task) => task.state === "SUCCESS")
      .length,
);

function formatTime(ts) {
  if (!ts) return "—";
  const date = new Date(ts * 1000);
  return date.toLocaleString();
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-start">
      <h5 class="mb-0">Completed Tasks</h5>
      <div class="ms-2">
        <span class="badge bg-info fs- me-2">total: {{ taskTotalCount }}</span>
        <span
          v-if="taskTotalSuccessCount > 0"
          class="badge bg-success fs-7 me-2"
          >success: {{ taskTotalSuccessCount }}</span
        >
        <span v-if="taskTotalFailureCount > 0" class="badge bg-danger fs-7 me-3"
          >failed: {{ taskTotalFailureCount }}</span
        >
      </div>
    </div>

    <div class="card-body">
      <div v-if="totalPages === 0" class="text-muted">No tasks found.</div>
      <div v-else class="accordion" :id="'taskAccordion-' + cardId">
        <div
          v-for="task in paginatedTasks"
          :key="task.uuid"
          class="accordion-item"
        >
          <h2 class="accordion-header" :id="'heading-' + task.uuid">
            <button
              class="accordion-button collapsed"
              type="button"
              data-bs-toggle="collapse"
              :data-bs-target="'#collapse-' + task.uuid"
              aria-expanded="false"
              :class="{ 'text-danger fw-bold': task.state === 'FAILURE' }"
              :aria-controls="'collapse-' + task.uuid"
            >
              {{ task.name }}
              <span class="ms-2 text-muted small">({{ task.state }})</span>
            </button>
          </h2>
          <div
            :id="'collapse-' + task.uuid"
            class="accordion-collapse collapse"
            :aria-labelledby="'heading-' + task.uuid"
            :data-bs-parent="'#taskAccordion-' + cardId"
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
                <!-- <li class="list-group-item"><strong>Runtime:</strong> {{ task.runtime.toFixed(2) }}s -->
                <!-- </li> -->
                <li class="list-group-item">
                  <strong>Received:</strong> {{ formatTime(task.received) }}
                </li>
                <li class="list-group-item">
                  <strong>Started:</strong> {{ formatTime(task.started) }}
                </li>
                <li class="list-group-item">
                  <strong>Succeeded:</strong> {{ formatTime(task.succeeded) }}
                </li>
                <li class="list-group-item">
                  <strong>Result:</strong> {{ task.result }}
                </li>
                <li class="list-group-item">
                  <pre>
                    {{ task.traceback }}
                  </pre>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div
      class="card-footer d-flex justify-content-center align-items-center gap-2"
    >
      <nav>
        <ul class="pagination justify-content-center">
          <li class="page-item">
            <a
              class="page-link"
              :class="{ disabled: currentPage === 1 }"
              @click="currentPage--"
              >Previous</a
            >
          </li>
          <li class="page-item">
            <a class="page-link disabled"
              >{{ currentPage }} of {{ totalPages }}
            </a>
          </li>
          <li class="page-item">
            <a
              class="page-link"
              :class="{ disabled: currentPage === totalPages }"
              @click="currentPage++"
              >Next</a
            >
          </li>
        </ul>
      </nav>
    </div>
  </div>
</template>
