<script setup>
import { ref } from "vue";
import { useTasksStore } from "@/stores";
import { storeToRefs } from "pinia";

const tasksStore = useTasksStore();
const { status } = storeToRefs(tasksStore);

const props = defineProps(["scheduled_task_id"]);
const emit = defineEmits(["scheduled-task-deleted"]);

const modalEl = ref(null);

defineExpose({
  modalEl,
});

function onSubmit() {
  return tasksStore
    .delete_scheduled_task(props.scheduled_task_id)
    .then(() => {
      emit("scheduled-task-deleted", {
        scheduled_task_id: props.scheduled_task_id,
      });
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    ref="modalEl"
    :id="'deleteScheduledTaskModal_' + scheduled_task_id"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="deleteScheduledTaskModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteScheduledTaskModal">
            Delete Scheduled Task #{{ scheduled_task_id }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          Are you sure you want to delete this scheduled task?
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
            class="btn btn-danger"
            :class="{ disabled: status.deleting }"
          >
            <span v-if="status.deleting">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.deleting">Delete</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
