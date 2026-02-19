<script setup>
import { computed, ref, nextTick } from "vue";
import { authHelper, formatSchedule } from "@/helpers";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAuthStore, useTasksStore } from "@/stores";
import ScheduledTaskActions from "@/components/tasks/ScheduledTaskActions.vue";
import CreateScheduledTaskModal from "@/components/tasks/CreateScheduledTaskModal.vue";

const authStore = useAuthStore();
const tasksStore = useTasksStore();

const { scopes } = storeToRefs(authStore);

defineProps({
  scheduledTasks: {
    type: Array,
    default: () => [],
  },
  cardId: {
    type: String,
    default: () => Math.random().toString(36).substring(2, 8),
  },
});

const actions = computed(() => ({
  create: authHelper.hasScope(scopes.value, "scheduled_tasks:create"),
}));

const createModal = ref(null);
const createModalRef = ref(null);

function getCreateModal() {
  if (!createModal.value && createModalRef.value?.modalEl) {
    createModal.value = new Modal(createModalRef.value.modalEl);
  }
  return createModal.value;
}

function openCreateScheduledTaskModal() {
  nextTick(() => {
    getCreateModal()?.show();
  });
}

function handleScheduledTaskCreated() {
  getCreateModal()?.hide();
  tasksStore.get_scheduled_tasks();
}

const formatDate = (isoString) => {
  if (!isoString) return "-";
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const statusColor = (status) => {
  switch (status) {
    case "scheduled":
      return "text-success";
    case "running":
      return "text-primary";
    case "error":
      return "text-danger";
    default:
      return "text-secondary";
  }
};
</script>

<style scoped>
.table td,
.table th {
  vertical-align: middle;
}
</style>

<template>
  <div :id="cardId" class="card my-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-between">
      <h5 class="mb-0">Scheduled Tasks</h5>
      <button
        v-if="actions.create"
        type="button"
        class="btn btn-outline-primary btn-sm"
        @click="openCreateScheduledTaskModal"
      >
        + New
      </button>
    </div>

    <div class="card-body p-0">
      <div class="m-4">
        <table class="table table-striped">
          <thead class="table">
            <tr>
              <th>task</th>
              <th>last run</th>
              <th>next run</th>
              <th>frequency</th>
              <th>total runs</th>
              <th>status</th>
              <th>actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="task in scheduledTasks" :key="task.id">
              <td>{{ task.task_name.replace("app.worker.tasks.", "") }}</td>
              <td>{{ formatDate(task.last_run_at) }}</td>
              <td>{{ formatDate(task.due_at) }}</td>
              <td>{{ formatSchedule(task.schedule) }}</td>
              <td>{{ task.total_run_count }}</td>
              <td :class="statusColor(task.status)">{{ task.status }}</td>
              <td>
                <ScheduledTaskActions :scheduled_task="task" />
              </td>
            </tr>
            <tr v-if="scheduledTasks.length === 0">
              <td colspan="7" class="text-center py-2">No scheduled tasks</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <CreateScheduledTaskModal
      ref="createModalRef"
      @scheduled-task-created="handleScheduledTaskCreated"
    />
  </div>
</template>
