<script setup>
import { ref, reactive, computed } from "vue";
import { useExportsStore, useToastsStore } from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";
import ExportScheduleFields from "@/components/exports/ExportScheduleFields.vue";

const props = defineProps({
  initialQuery: { type: String, default: "" },
  initialIndexTarget: { type: String, default: "attributes" },
});

const exportsStore = useExportsStore();
const toastsStore = useToastsStore();

const emit = defineEmits(["created", "close"]);

const exportJob = reactive({
  name: "",
  query: props.initialQuery,
  index_target: props.initialIndexTarget,
  format: "json",
  distribution: null,
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

const stixDisabled = computed(() => exportJob.index_target === "events");

function onIndexTargetChange() {
  // STIX export of bare events carries no indicators; steer back to JSON.
  if (stixDisabled.value && exportJob.format === "stix") {
    exportJob.format = "json";
  }
}

function reset() {
  exportJob.name = "";
  exportJob.query = props.initialQuery;
  exportJob.index_target = props.initialIndexTarget;
  exportJob.format = "json";
  exportJob.distribution = null;
  scheduleModel.value = { schedule: null, schedule_enabled: false };
  apiError.value = null;
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
      reset();
      emit("created", response);
    })
    .catch((err) => (apiError.value = err?.message || String(err)));
}

function close() {
  reset();
  emit("close");
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 2rem 1rem;
  z-index: 1050;
}
.modal-card {
  width: 720px;
  max-width: calc(100% - 2rem);
  max-height: calc(100vh - 4rem);
  display: flex;
  flex-direction: column;
}
.modal-card > .card {
  max-height: 100%;
  display: flex;
  flex-direction: column;
}
.modal-card .card-body {
  overflow-y: auto;
}
</style>

<template>
  <div class="modal-backdrop" @click.self="close">
    <div class="modal-card">
      <div class="card">
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <strong>New Export</strong>
          <button type="button" class="btn-close" @click="close" />
        </div>

        <div class="card-body">
          <p class="text-muted small mb-3">
            Run an OpenSearch query and store the matching IOCs as a
            downloadable file. The export runs in the background; track its
            progress on the exports page.
          </p>

          <div class="mb-3">
            <label class="form-label" for="modal-export-name">Name</label>
            <input
              id="modal-export-name"
              class="form-control"
              v-model="exportJob.name"
              placeholder="e.g. Network IOCs — last 30 days"
              autofocus
            />
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-export-target"
              >Search index</label
            >
            <select
              id="modal-export-target"
              class="form-select"
              v-model="exportJob.index_target"
              @change="onIndexTargetChange"
            >
              <option value="attributes">Attributes</option>
              <option value="events">Events</option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label" for="modal-export-query"
              >Lucene Query</label
            >
            <textarea
              id="modal-export-query"
              class="form-control font-monospace"
              rows="4"
              v-model="exportJob.query"
              placeholder="e.g. type:ip-dst AND to_ids:true"
            />
            <LuceneQuerySyntaxHint />
          </div>

          <div class="mb-2">
            <label class="form-label" for="modal-export-format">Format</label>
            <select
              id="modal-export-format"
              class="form-select"
              v-model="exportJob.format"
            >
              <option value="json">JSON</option>
              <option value="misp">JSON (MISP)</option>
              <option value="csv">CSV</option>
              <option value="stix" :disabled="stixDisabled">
                STIX 2.1{{ stixDisabled ? " (attributes only)" : "" }}
              </option>
            </select>
            <div class="form-text">
              STIX 2.1 groups matching attributes into events and converts them
              via the misp-stix library.
            </div>
          </div>

          <div v-if="isMisp" class="mb-2">
            <label class="form-label" for="modal-export-distribution"
              >Distribution</label
            >
            <select
              id="modal-export-distribution"
              class="form-select"
              v-model.number="exportJob.distribution"
            >
              <option :value="null" disabled>
                Select a distribution level…
              </option>
              <option
                v-for="opt in DISTRIBUTION_OPTIONS"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
            <div class="form-text">
              All matches are merged into a single MISP event with this
              distribution level. Correlation stays enabled.
            </div>
          </div>

          <hr />
          <ExportScheduleFields v-model="scheduleModel" />

          <div v-if="apiError" class="alert alert-danger mt-3 mb-0">
            {{ apiError }}
          </div>
        </div>

        <div class="card-footer d-flex justify-content-end gap-2">
          <button class="btn btn-outline-secondary" @click="close">
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
  </div>
</template>
