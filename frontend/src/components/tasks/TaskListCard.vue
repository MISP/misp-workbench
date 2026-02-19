<script setup>
import { faHourglassHalf, faWarning } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, computed } from "vue";

const activeFilter = ref("ALL"); // ALL | SUCCESS | FAILURE

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
  Math.ceil(filteredTasks.value.length / props.pageSize),
);

const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize;
  return filteredTasks.value.slice(start, start + props.pageSize);
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

const filteredTasks = computed(() => {
  let list = Object.values(props.tasks);

  if (activeFilter.value === "SUCCESS") {
    list = list.filter((task) => task.state === "SUCCESS");
  }

  if (activeFilter.value === "FAILURE") {
    list = list.filter((task) => task.state === "FAILURE");
  }

  return list.sort((a, b) => b.timestamp - a.timestamp);
});

function formatTime(ts) {
  if (!ts) return "—";
  const date = new Date(ts * 1000);
  return date.toLocaleString();
}
</script>

<style scoped>
.badge[role="button"] {
  cursor: pointer;
}
</style>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-start">
      <h5 class="mb-0">Completed Tasks</h5>
      <div class="ms-2">
        <span
          class="badge me-2 bg-info"
          :class="
            activeFilter === 'ALL'
              ? 'shadow border border-warning-subtle'
              : 'fw-light'
          "
          role="button"
          @click="
            activeFilter = 'ALL';
            currentPage = 1;
          "
        >
          total: {{ taskTotalCount }}
        </span>
        <span
          v-if="taskTotalSuccessCount > 0"
          class="badge me-2 bg-success"
          :class="
            activeFilter === 'SUCCESS'
              ? 'shadow border border-warning-subtle'
              : 'fw-light'
          "
          role="button"
          @click="
            activeFilter = 'SUCCESS';
            currentPage = 1;
          "
        >
          succeeded: {{ taskTotalSuccessCount }}
        </span>
        <span
          v-if="taskTotalFailureCount > 0"
          class="badge me-3 bg-danger"
          :class="
            activeFilter === 'FAILURE'
              ? 'shadow border border-warning-subtle'
              : 'fw-light'
          "
          role="button"
          @click="
            activeFilter = 'FAILURE';
            currentPage = 1;
          "
        >
          failed: {{ taskTotalFailureCount }}
        </span>
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
              <FontAwesomeIcon
                v-if="task.state === 'FAILURE'"
                :icon="faWarning"
                class="ms-2 text-warning"
              />
              <FontAwesomeIcon
                v-if="task.runtime > 1"
                :icon="faHourglassHalf"
                class="ms-2 text-secondary"
              />
            </button>
          </h2>
          <div
            :id="'collapse-' + task.uuid"
            class="accordion-collapse collapse"
            :aria-labelledby="'heading-' + task.uuid"
            :data-bs-parent="'#taskAccordion-' + cardId"
          >
            <div class="accordion-body small">
              {{ task }}
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
                <li class="list-group-item">
                  <strong>Succeeded:</strong> {{ formatTime(task.succeeded) }}
                </li>
                <li class="list-group-item">
                  <strong>Runtime:</strong>
                  {{ task.runtime ? task.runtime.toFixed(4) + "s" : "" }}
                </li>
                <li class="list-group-item">
                  <strong>Result:</strong> {{ task.result }}
                </li>
                <li class="list-group-item" v-if="task.traceback">
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
