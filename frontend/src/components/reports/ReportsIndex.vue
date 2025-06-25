<script setup>
import { storeToRefs } from "pinia";
import { useReportsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ReportActions from "@/components/reports/ReportActions.vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

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
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading reports: {{ status.error }}
  </div>
  <div v-if="!status.loading && reports.length === 0">
    <div class="alert alert-info" role="alert">
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
          <div class="accordion-body bg-white">
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
