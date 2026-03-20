<script setup>
import { storeToRefs } from "pinia";
import { useReportsStore } from "@/stores";
import ReportActions from "@/components/reports/ReportActions.vue";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["event_uuid"]);
const reportsStore = useReportsStore();
const { reports, status } = storeToRefs(reportsStore);

const emit = defineEmits(["report-updated", "report-deleted"]);

function handleReportDeleted(r) {
  emit("report-deleted", r);
}

function handleReportUpdated(r) {
  emit("report-updated", r);
}

reportsStore.getReportsByEventId(props.event_uuid);
</script>

<template>
  <div v-if="status.error" class="text-danger">
    Error loading reports: {{ status.error }}
  </div>
  <span v-if="status.loading">
    <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
  </span>
  <div v-if="!status.loading && reports.length === 0">
    <div class="alert alert-secondary" role="alert">
      No event reports found for this event.
    </div>
  </div>
  <div class="table-responsive-sm">
    <div class="accordion" id="eventReporstAccordion" style="overflow-y: auto">
      <div
        class="accordion-item"
        style="max-height: 800px; overflow-y: auto"
        :key="report._id"
        v-for="report in reports"
      >
        <div
          class="accordion-header d-flex align-items-center"
          :id="`eventReportHeading${report._id}`"
        >
          <button
            class="accordion-button flex-grow-1 text-start"
            type="button"
            data-bs-toggle="collapse"
            :data-bs-target="`#eventReport${report._id}`"
            aria-expanded="true"
          >
            <strong>{{ report._source.name }}</strong>
          </button>
          <div class="ms-2">
            <ReportActions
              :report="report"
              :key="report._id"
              @report-updated="handleReportUpdated"
              @report-deleted="handleReportDeleted"
            />
          </div>
        </div>

        <div
          :id="`eventReport${report._id}`"
          class="accordion-collapse collapse"
          :class="{
            show: report._id === reports[0]._id,
          }"
          data-bs-parent="#eventReporstAccordion"
        >
          <div class="accordion-body">
            <div
              class="markdown-body"
              v-html="DOMPurify.sanitize(marked(report._source.content))"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-body {
  color: var(--bs-body-color);
  background-color: transparent;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  color: var(--bs-body-color);
}

.markdown-body :deep(a) {
  color: var(--bs-link-color);
}

.markdown-body :deep(code) {
  background-color: var(--bs-secondary-bg);
  color: var(--bs-body-color);
  padding: 0.15em 0.35em;
  border-radius: 0.25rem;
}

.markdown-body :deep(pre) {
  background-color: var(--bs-secondary-bg);
  border: 1px solid var(--bs-border-color);
  border-radius: 0.375rem;
  padding: 1rem;
}

.markdown-body :deep(pre code) {
  background-color: transparent;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--bs-border-color);
  color: var(--bs-secondary-color);
  padding-left: 1rem;
  margin-left: 0;
}

.markdown-body :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.markdown-body :deep(table th),
.markdown-body :deep(table td) {
  border: 1px solid var(--bs-border-color);
  padding: 0.5rem 0.75rem;
  background-color: transparent;
}

.markdown-body :deep(table tr),
.markdown-body :deep(table tr:nth-child(even)),
.markdown-body :deep(table tr:nth-child(odd)) {
  background-color: transparent;
}

.markdown-body :deep(table thead th) {
  background-color: var(--bs-secondary-bg);
}

.markdown-body :deep(hr) {
  border-color: var(--bs-border-color);
}
</style>
