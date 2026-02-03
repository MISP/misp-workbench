<script setup>
import { storeToRefs } from "pinia";
import { useRemoteMISPReportsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

const props = defineProps(["server_id", "event_id"]);
const remoteMISPReportsStore = useRemoteMISPReportsStore();
const { remote_event_reports, status } = storeToRefs(remoteMISPReportsStore);

remoteMISPReportsStore.get_remote_server_event_reports(
  props.server_id,
  props.event_id,
);
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading reports: {{ status.error }}
  </div>
  <div v-if="!status.loading && remote_event_reports.length === 0">
    <div class="alert alert-secondary" role="alert">
      No event reports found for this event.
    </div>
  </div>
  <div class="table-responsive-sm">
    <div class="accordion" id="eventReporstAccordion" style="overflow-y: auto">
      <div
        class="accordion-item"
        style="max-height: 800px; overflow-y: auto"
        :key="report.EventReport.id"
        v-for="report in remote_event_reports"
      >
        <h2
          class="accordion-header"
          :id="`eventReportHeading${report.EventReport.id}`"
        >
          <button
            class="accordion-button"
            type="button"
            data-bs-toggle="collapse"
            :data-bs-target="`#eventReport${report.EventReport.id}`"
            aria-expanded="true"
          >
            <strong>{{ report.EventReport.name }} </strong>
          </button>
        </h2>
        <div
          :id="`eventReport${report.EventReport.id}`"
          class="accordion-collapse collapse"
          :class="{
            show:
              report.EventReport.id === remote_event_reports[0].EventReport.id,
          }"
          data-bs-parent="#eventReporstAccordion"
        >
          <div class="accordion-body">
            <div
              class="markdown-body"
              v-html="DOMPurify.sanitize(marked(report.EventReport.content))"
            ></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
