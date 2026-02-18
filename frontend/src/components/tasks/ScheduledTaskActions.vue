<script setup>
import { computed, ref, nextTick } from "vue";
import { authHelper } from "@/helpers";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faCog,
  faTrash,
  faPlay,
  faStop,
} from "@fortawesome/free-solid-svg-icons";
import { useAuthStore, useTasksStore } from "@/stores";
import DeleteScheduledTaskModal from "@/components/tasks/DeleteScheduledTaskModal.vue";
import ConfigureScheduledTaskModal from "@/components/tasks/ConfigureScheduledTaskModal.vue";

const tasksStore = useTasksStore();
const authStore = useAuthStore();

const props = defineProps({
  scheduled_task: Object,
  default_actions: {
    type: Object,
    default: () => ({}),
  },
});

const { scopes } = storeToRefs(authStore);

const actions = computed(() => ({
  index:
    props.default_actions.index ??
    authHelper.hasScope(scopes.value, "scheduled_tasks:index"),
  view:
    props.default_actions.view ??
    authHelper.hasScope(scopes.value, "scheduled_tasks:view"),
  update:
    props.default_actions.update ??
    authHelper.hasScope(scopes.value, "scheduled_tasks:update"),
  delete:
    props.default_actions.delete ??
    authHelper.hasScope(scopes.value, "scheduled_tasks:delete"),
  create:
    props.default_actions.create ??
    authHelper.hasScope(scopes.value, "scheduled_tasks:create"),
}));

const deleteModal = ref(null);
const deleteModalRef = ref(null);
const configureModal = ref(null);
const configureModalRef = ref(null);

function getDeleteModal() {
  if (!deleteModal.value && deleteModalRef.value?.modalEl) {
    deleteModal.value = new Modal(deleteModalRef.value.modalEl);
  }
  return deleteModal.value;
}

function getConfigureModal() {
  if (!configureModal.value && configureModalRef.value?.modalEl) {
    configureModal.value = new Modal(configureModalRef.value.modalEl);
  }
  return configureModal.value;
}

function openDeleteScheduledTaskModal() {
  nextTick(() => {
    getDeleteModal()?.show();
  });
}

function openConfigureScheduledTaskModal() {
  nextTick(() => {
    getConfigureModal()?.show();
  });
}

function toggleEnable(scheduled_task_id) {
  tasksStore.update_scheduled_task(scheduled_task_id, {
    enabled: !props.scheduled_task.enabled,
  });
}

function handleScheduledTaskDeleted() {
  getDeleteModal()?.hide();
  // Refresh the scheduled tasks list after deletion
  tasksStore.get_scheduled_tasks();
}

function handleScheduledTaskUpdated() {
  getConfigureModal()?.hide();
  // Refresh the scheduled tasks list after update
  tasksStore.get_scheduled_tasks();
}
</script>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-sm"
        :class="
          scheduled_task.enabled ? 'btn-outline-danger' : 'btn-outline-success'
        "
        :title="
          scheduled_task.enabled
            ? 'Disable Scheduled Task'
            : 'Enable Scheduled Task'
        "
        @click.stop="toggleEnable(scheduled_task.id)"
      >
        <FontAwesomeIcon :icon="scheduled_task.enabled ? faStop : faPlay" />
      </button>
      <button
        v-if="actions.update"
        type="button"
        class="btn btn-outline-primary btn-sm"
        title="Configure Scheduled Task"
        @click="openConfigureScheduledTaskModal"
      >
        <FontAwesomeIcon :icon="faCog" />
      </button>
      <button
        v-if="actions.delete"
        type="button"
        class="btn btn-danger btn-sm"
        title="Delete Scheduled Task"
        @click="openDeleteScheduledTaskModal"
      >
        <FontAwesomeIcon :icon="faTrash" fixed-width />
      </button>
    </div>
    <DeleteScheduledTaskModal
      ref="deleteModalRef"
      :scheduled_task_id="scheduled_task.id"
      @scheduled-task-deleted="handleScheduledTaskDeleted"
    />
    <ConfigureScheduledTaskModal
      ref="configureModalRef"
      :scheduled_task="scheduled_task"
      @scheduled-task-updated="handleScheduledTaskUpdated"
    />
  </div>
</template>
