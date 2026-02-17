<script setup>
import { ref } from "vue";
import { useTasksStore } from "@/stores";
import { storeToRefs } from "pinia";

const tasksStore = useTasksStore();
const { status } = storeToRefs(tasksStore);

const props = defineProps({
  scheduled_task: Object,
});

const emit = defineEmits(["scheduled-task-updated"]);

const modalEl = ref(null);

defineExpose({
  modalEl,
});

function onSubmit() {
  emit("scheduled-task-updated", {
    scheduled_task_id: props.scheduled_task.id,
  });
}
</script>

<template>
  <div
    ref="modalEl"
    :id="'configureScheduledTaskModal_' + scheduled_task.id"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="configureScheduledTaskModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="configureScheduledTaskModal">
            Configure Scheduled Task #{{ scheduled_task.id }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          {{ scheduled_task }}
        </div>
        <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
          {{ status.error }}
        </div>
        <div class="modal-footer">
          <button
            id="closeModalButton"
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Discard
          </button>
          <button
            type="submit"
            @click="onSubmit"
            class="btn btn-outline-primary"
            :class="{ disabled: status.loading }"
          >
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.loading">Save</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
