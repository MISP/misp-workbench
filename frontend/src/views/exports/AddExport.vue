<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import {
  useExportsStore,
  useToastsStore,
  useDetectionProfilesStore,
} from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";
import ExportScheduleFields from "@/components/exports/ExportScheduleFields.vue";
import DetectionFormatOptions from "@/components/exports/DetectionFormatOptions.vue";

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
  profile_id: null,
  format_options: {
    rule_action: "alert",
    rpz_policy: "nxdomain",
    rpz_redirect: "",
  },
});

// A detection profile decides what the export holds (and whether as
// indicators or attributes); the query then only narrows it.
const profilesStore = useDetectionProfilesStore();
profilesStore.getAll();
const profile = computed(() =>
  profilesStore.profiles.find((p) => p.id === exportJob.profile_id),
);
function onProfileChange() {
  if (profile.value) {
    exportJob.index_target = profile.value.granularity;
    if (!exportJob.query) exportJob.query = "*";
    if (!STREAMED_FORMATS.includes(exportJob.format)) {
      exportJob.format = "ndjson";
    }
  }
  onFormatChange();
}

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
const STREAMED_FORMATS = ["ndjson", "text", "cdb", "suricata", "zeek", "rpz"];
// What one value turns into: a line, a rule, an intel item, a zone record.
const LINE_FORMATS = ["text", "cdb", "suricata", "zeek", "rpz"];
const DETECTION_FORMATS = ["suricata", "zeek", "rpz"];
const stixDisabled = computed(
  () => exportJob.index_target !== "attributes" || !!profile.value,
);
const recordFormatsDisabled = computed(
  () => isIndicators.value || !!profile.value,
);
// One value per line, so events have nothing to put there.
const lineFormatsDisabled = computed(() => exportJob.index_target === "events");
// Deltas carry deletions (ndjson tombstones) and key off write times, which
// attributes and indicators have.
// A profile feed's removals are an indicator's: it needs indicators.
const canBeIncremental = computed(
  () =>
    exportJob.format === "ndjson" &&
    exportJob.index_target !== "events" &&
    (!profile.value || profile.value.granularity === "indicators"),
);

function onIndexTargetChange() {
  if (isIndicators.value && !STREAMED_FORMATS.includes(exportJob.format)) {
    exportJob.format = "ndjson";
  }
  // STIX export of bare events carries no indicators; steer back to JSON.
  if (stixDisabled.value && exportJob.format === "stix") {
    exportJob.format = "json";
  }
  if (lineFormatsDisabled.value && LINE_FORMATS.includes(exportJob.format)) {
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
        <label class="form-label" for="export-profile">Detection profile</label>
        <select
          id="export-profile"
          class="form-select"
          v-model="exportJob.profile_id"
          @change="onProfileChange"
        >
          <option :value="null">None: choose what to export below</option>
          <option v-for="p in profilesStore.profiles" :key="p.id" :value="p.id">
            {{ p.name }} ({{ p.granularity }})
          </option>
        </select>
        <div class="form-text">
          A profile decides what the export holds. The query below then only
          narrows it (<code>*</code> for all of it).
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label" for="export-target">Search index</label>
        <select
          id="export-target"
          class="form-select"
          v-model="exportJob.index_target"
          :disabled="!!profile"
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
          <optgroup label="Detection engines">
            <option value="suricata" :disabled="lineFormatsDisabled">
              Suricata rules{{ lineFormatsDisabled ? " (not for events)" : "" }}
            </option>
            <option value="zeek" :disabled="lineFormatsDisabled">
              Zeek Intel{{ lineFormatsDisabled ? " (not for events)" : "" }}
            </option>
            <option value="rpz" :disabled="lineFormatsDisabled">
              DNS RPZ zone{{ lineFormatsDisabled ? " (not for events)" : "" }}
            </option>
          </optgroup>
        </select>
        <div class="form-text">
          STIX 2.1 groups matching attributes into events and converts them via
          the misp-stix library. NDJSON, plain text, Wazuh CDB and the detection
          engines' formats are streamed straight into storage, with no record
          limit.
        </div>
      </div>

      <div v-if="DETECTION_FORMATS.includes(exportJob.format)" class="mb-4">
        <DetectionFormatOptions
          v-model="exportJob.format_options"
          :format="exportJob.format"
        />
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
