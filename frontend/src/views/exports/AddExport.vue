<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useExportsStore, useToastsStore } from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";
import ExportScheduleFields from "@/components/exports/ExportScheduleFields.vue";

const exportsStore = useExportsStore();
const toastsStore = useToastsStore();

const exportJob = reactive({
  name: "",
  query: "",
  // Consolidated indicators by default: each value once, with its context,
  // which is what security controls want.
  index_target: "indicators",
  format: "ndjson",
  distribution: null,
  incremental: false,
});

const scheduleModel = ref({ schedule: null, schedule_enabled: false });

const apiError = ref(null);

// MISP exports build a single event, so an event distribution level is required.
const DISTRIBUTION_OPTIONS = [
  { value: 0, label: "Your organisation only" },
  { value: 1, label: "This community only" },
  { value: 2, label: "Connected communities" },
  { value: 3, label: "All communities" },
];

const isMisp = computed(() => exportJob.format === "misp");

const canSubmit = computed(
  () =>
    exportJob.name &&
    exportJob.query &&
    (!isMisp.value || exportJob.distribution !== null),
);

const isIndicators = computed(() => exportJob.index_target === "indicators");
// Indicators are only written by the streamed exporter.
const STREAMED_FORMATS = ["ndjson", "text", "cdb"];
const stixDisabled = computed(() => exportJob.index_target !== "attributes");
const recordFormatsDisabled = computed(() => isIndicators.value);
// One value per line, so events have nothing to put there.
const lineFormatsDisabled = computed(() => exportJob.index_target === "events");
// Deltas carry deletions (ndjson tombstones) and key off write times, which
// attributes and indicators have.
const canBeIncremental = computed(
  () => exportJob.format === "ndjson" && exportJob.index_target !== "events",
);

function onIndexTargetChange() {
  if (isIndicators.value && !STREAMED_FORMATS.includes(exportJob.format)) {
    exportJob.format = "ndjson";
  }
  // STIX export of bare events carries no indicators; steer back to JSON.
  if (stixDisabled.value && exportJob.format === "stix") {
    exportJob.format = "json";
  }
  if (lineFormatsDisabled.value && ["text", "cdb"].includes(exportJob.format)) {
    exportJob.format = "json";
  }
  onFormatChange();
}

function onFormatChange() {
  if (!canBeIncremental.value) {
    exportJob.incremental = false;
  }
}

async function submit() {
  apiError.value = null;
  await exportsStore
    .create({
      ...exportJob,
      schedule: scheduleModel.value.schedule,
      schedule_enabled: scheduleModel.value.schedule_enabled,
    })
    .then((response) => {
      toastsStore.push(
        `Export "${response.name}" queued. It will be ready shortly.`,
        "success",
      );
      router.push("/exports");
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function cancel() {
  router.push("/exports");
}
</script>

<template>
  <div class="card mx-auto" style="max-width: 720px">
    <div class="card-header border-bottom">
      <h4 class="mb-0">New Export</h4>
    </div>
    <div class="card-body">
      <p class="text-muted mb-4">
        Run an OpenSearch query and store the matching IOCs as a downloadable
        file. The export runs in the background; refresh the list to track its
        progress.
      </p>

      <div class="mb-3">
        <label class="form-label" for="export-name">Name</label>
        <input
          id="export-name"
          class="form-control"
          v-model="exportJob.name"
          placeholder="e.g. Network IOCs — last 30 days"
        />
      </div>

      <div class="mb-3">
        <label class="form-label" for="export-target">Search index</label>
        <select
          id="export-target"
          class="form-select"
          v-model="exportJob.index_target"
          @change="onIndexTargetChange"
        >
          <option value="indicators">
            Indicators (one per type and value)
          </option>
          <option value="attributes">Attributes</option>
          <option value="events">Events</option>
        </select>
        <div v-if="isIndicators" class="form-text">
          Consolidated indicators: each value once, with its sources, first and
          last seen, merged tags and sightings across every event.
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label" for="export-query">Lucene Query</label>
        <textarea
          id="export-query"
          class="form-control font-monospace"
          rows="4"
          v-model="exportJob.query"
          placeholder="e.g. type:ip-dst AND to_ids:true"
        />
        <LuceneQuerySyntaxHint />
      </div>

      <div class="mb-4">
        <label class="form-label" for="export-format">Format</label>
        <select
          id="export-format"
          class="form-select"
          v-model="exportJob.format"
          @change="onFormatChange"
        >
          <option value="json" :disabled="recordFormatsDisabled">JSON</option>
          <option value="misp" :disabled="recordFormatsDisabled">
            JSON (MISP)
          </option>
          <option value="csv" :disabled="recordFormatsDisabled">CSV</option>
          <option value="stix" :disabled="stixDisabled">
            STIX 2.1{{ stixDisabled ? " (attributes only)" : "" }}
          </option>
          <option value="ndjson">NDJSON (one record per line)</option>
          <option value="text" :disabled="lineFormatsDisabled">
            Plain text, one value per line{{
              lineFormatsDisabled ? " (not for events)" : ""
            }}
          </option>
          <option value="cdb" :disabled="lineFormatsDisabled">
            Wazuh CDB list{{ lineFormatsDisabled ? " (not for events)" : "" }}
          </option>
        </select>
        <div class="form-text">
          STIX 2.1 groups matching attributes into events and converts them via
          the misp-stix library. NDJSON, plain text and Wazuh CDB are streamed
          straight into storage, with no record limit.
        </div>
      </div>

      <div v-if="canBeIncremental" class="mb-4">
        <div class="form-check form-switch">
          <input
            id="export-incremental"
            class="form-check-input"
            type="checkbox"
            v-model="exportJob.incremental"
          />
          <label class="form-check-label" for="export-incremental">
            Incremental feed
          </label>
        </div>
        <div class="form-text">
          Each run also stores what changed since the previous one, deletions
          included. Consumers poll the export's feed URL and only download those
          changes. Pair it with a schedule.
        </div>
      </div>

      <div v-if="isMisp" class="mb-4">
        <label class="form-label" for="export-distribution">Distribution</label>
        <select
          id="export-distribution"
          class="form-select"
          v-model.number="exportJob.distribution"
        >
          <option :value="null" disabled>Select a distribution level…</option>
          <option
            v-for="opt in DISTRIBUTION_OPTIONS"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
        <div class="form-text">
          All matches are merged into a single MISP event with this distribution
          level. Correlation stays enabled.
        </div>
      </div>

      <hr />
      <div class="mb-4">
        <ExportScheduleFields v-model="scheduleModel" />
      </div>

      <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

      <div class="d-flex justify-content-end gap-2">
        <button class="btn btn-outline-secondary" @click="cancel">
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || exportsStore.status.creating"
          @click="submit"
        >
          {{ exportsStore.status.creating ? "Queuing…" : "Create Export" }}
        </button>
      </div>
    </div>
  </div>
</template>
