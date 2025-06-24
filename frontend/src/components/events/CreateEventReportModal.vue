<script setup>
import { ref } from "vue";
import { useReportsStore } from "@/stores";
import { storeToRefs } from "pinia";

const reportsStore = useReportsStore();
const { status } = storeToRefs(eventsStore);

const props = defineProps(["event_uuid", "modal"]);
const emit = defineEmits(["event-report-created"]);

const report = ref(null);

function onSubmit() {
  return reportsStore
    .create(props.event_uuid, report)
    .then(() => {
      emit("event-report-created", { event_uuid: props.event_uuid });
      props.modal.hide();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    :id="'createEventReportModal_' + event_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="createEventReportModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="createEventReportModal">
            Create Event Report
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">Event Report Editor</div>
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
            <span v-if="!status.deleting">Create</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
