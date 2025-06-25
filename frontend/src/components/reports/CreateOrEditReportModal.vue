<script setup>
import { marked } from "marked";
import DOMPurify from "dompurify";
import { ref, computed } from "vue";
import { useReportsStore } from "@/stores";
import { storeToRefs } from "pinia";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTableColumns,
  faPen,
  faEye,
} from "@fortawesome/free-solid-svg-icons";

const reportsStore = useReportsStore();
const { status } = storeToRefs(reportsStore);

const props = defineProps({
  event_uuid: String,
  modal: Object,
  existing_report: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["report-created", "report-updated"]);

const report = ref({
  name: props.existing_report ? props.existing_report._source.name : "",
  content: props.existing_report ? props.existing_report._source.content : "",
  uuid: props.existing_report ? props.existing_report._id : null,
  event_uuid: props.event_uuid,
});

const viewMode = ref("split"); // 'split', 'source', 'preview'

const renderedMarkdown = computed(() =>
  DOMPurify.sanitize(marked(report.value.content)),
);

function onSubmit() {
  if (props.existing_report && props.existing_report._id) {
    // Update existing report
    return reportsStore
      .update(report.value.uuid, report.value)
      .then((response) => {
        emit("report-updated", { response });
        props.modal.hide();
      })
      .catch((error) => (status.error = error));
  } else {
    // Create new report
    return reportsStore
      .create(props.event_uuid, report.value)
      .then((response) => {
        emit("report-created", { response });
        props.modal.hide();
      })
      .catch((error) => (status.error = error));
  }
}
</script>

<template>
  <div
    :id="'createOrEditReportModal_' + event_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="createOrEditReportModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-fullscreen">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="createOrEditReportModal">
            {{
              props.existing_report
                ? "Edit Event Report"
                : "Create Event Report"
            }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>

        <div class="modal-body">
          <div class="mb-3 d-flex gap-2 text-end">
            <div class="btn-group" role="group" aria-label="Editor mode">
              <button
                class="btn btn-outline-secondary btn-sm"
                :class="{ active: viewMode === 'split' }"
                @click="viewMode = 'split'"
              >
                <FontAwesomeIcon :icon="faTableColumns" />
              </button>
              <button
                class="btn btn-outline-secondary btn-sm"
                :class="{ active: viewMode === 'preview' }"
                @click="viewMode = 'preview'"
              >
                <FontAwesomeIcon :icon="faEye" />
              </button>
              <button
                class="btn btn-outline-secondary btn-sm"
                :class="{ active: viewMode === 'source' }"
                @click="viewMode = 'source'"
              >
                <FontAwesomeIcon :icon="faPen" />
              </button>
            </div>
          </div>

          <!-- Title -->
          <div class="mb-3">
            <label for="reportTitle" class="form-label">Title</label>
            <input
              type="text"
              id="reportTitle"
              v-model="report.name"
              class="form-control"
              placeholder="Enter report name..."
            />
          </div>

          <div class="d-flex gap-3" style="height: 70vh">
            <!-- Markdown Input -->
            <textarea
              v-show="viewMode === 'source' || viewMode === 'split'"
              v-model="report.content"
              class="form-control"
              :class="{
                'w-100': viewMode === 'source',
                'w-50': viewMode === 'split',
              }"
              placeholder="Write your markdown here..."
              style="resize: none"
            ></textarea>

            <div
              v-show="viewMode === 'preview' || viewMode === 'split'"
              class="form-control overflow-auto border"
              :class="{
                'w-100': viewMode === 'preview',
                'w-50': viewMode === 'split',
              }"
              v-html="renderedMarkdown"
            ></div>
          </div>

          <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
            {{ status.error }}
          </div>
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
            class="btn btn-primary"
            :class="{ disabled: status.creating }"
          >
            <span v-if="status.creating">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.creating">
              {{ props.existing_report ? "Update" : "Create" }}
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
textarea {
  height: 100%;
}
</style>
