<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { Modal } from "bootstrap";
import { useEventsStore } from "@/stores";
import { storeToRefs } from "pinia";
import { errorMessage } from "@/helpers/error-handler";

const eventsStore = useEventsStore();
const { status } = storeToRefs(eventsStore);

const props = defineProps(["event_uuid"]);
const emit = defineEmits(["event-deleted"]);

const modalEl = ref(null);
const hardDelete = ref(false);
const error = ref(null);

defineExpose({
  modalEl,
});

// Opened again, it doesn't show the last attempt's error.
function reset() {
  error.value = null;
}
onMounted(() => modalEl.value?.addEventListener("hidden.bs.modal", reset));
onBeforeUnmount(() =>
  modalEl.value?.removeEventListener("hidden.bs.modal", reset),
);

function onSubmit() {
  error.value = null;
  return eventsStore
    .delete(props.event_uuid, { force: hardDelete.value })
    .then(() => {
      emit("event-deleted", {
        event_uuid: props.event_uuid,
        force: hardDelete.value,
      });
      Modal.getInstance(modalEl.value)?.hide();
    })
    .catch((e) => (error.value = errorMessage(e)));
}
</script>

<template>
  <div
    ref="modalEl"
    :id="'deleteEventModal_' + event_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="deleteEventModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteEventModal">
            Delete Event #{{ event_uuid }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <p class="mb-3">Are you sure you want to delete this event?</p>
          <div class="form-check">
            <input
              class="form-check-input"
              type="checkbox"
              :id="'hardDeleteCheck_' + event_uuid"
              v-model="hardDelete"
            />
            <label
              class="form-check-label"
              :for="'hardDeleteCheck_' + event_uuid"
            >
              Hard delete (permanently remove, not recoverable)
            </label>
            <div class="form-text text-muted">
              By default the event is soft-deleted and can be restored. Hard
              delete removes the event and all its attributes, objects, tags and
              reports permanently.
            </div>
          </div>
        </div>
        <div v-if="error" class="alert alert-danger mx-3 mb-0" role="alert">
          {{ error }}
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
