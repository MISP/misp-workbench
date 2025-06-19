<script setup>
import { storeToRefs } from "pinia";
import { useReportsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

const props = defineProps(["event_uuid"]);
const reportsStore = useReportsStore();
const { reports, status } = storeToRefs(reportsStore);

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
        :key="report._source.id"
        v-for="report in reports"
      >
        <h2
          class="accordion-header"
          :id="`eventReportHeading${report._source.id}`"
        >
          <button
            class="accordion-button"
            type="button"
            data-bs-toggle="collapse"
            :data-bs-target="`#eventReport${report._source.id}`"
            aria-expanded="true"
          >
            <strong>{{ report._source.name }} </strong>
          </button>
        </h2>
        <div
          :id="`eventReport${report._source.id}`"
          class="accordion-collapse collapse"
          :class="{
            show: report._source.id === reports[0]._source.id,
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
