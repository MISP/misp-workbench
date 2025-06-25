<script setup>
import { storeToRefs } from "pinia";
import { useReportsStore } from "../../stores/reports.store";

const reportsStore = useReportsStore();
const { status } = storeToRefs(reportsStore);

const props = defineProps(["report_uuid", "modal"]);
const emit = defineEmits(["report-deleted"]);

function onSubmit() {
  return reportsStore
    .delete(props.report_uuid)
    .then(() => {
      emit("report-deleted", { report_uuid: props.report_uuid });
      props.modal.hide();
    })
    .catch((error) => (status.error = error));
}
</script>

<template>
  <div
    :id="'deleteReportModal_' + report_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="deleteReportModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="deleteReportModal">
            Delete Report #{{ report_uuid }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          Are you sure you want to delete this report?
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
