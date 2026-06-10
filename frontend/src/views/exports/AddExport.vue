<script setup>
import { ref, reactive, computed } from "vue";
import { router } from "@/router";
import { useExportsStore, useToastsStore } from "@/stores";
import LuceneQuerySyntaxHint from "@/components/misc/LuceneQuerySyntaxHint.vue";

const exportsStore = useExportsStore();
const toastsStore = useToastsStore();

const exportJob = reactive({
  name: "",
  query: "",
  index_target: "attributes",
  format: "json",
});

const apiError = ref(null);

const canSubmit = computed(() => exportJob.name && exportJob.query);

const stixDisabled = computed(() => exportJob.index_target === "events");

function onIndexTargetChange() {
  // STIX export of bare events carries no indicators; steer back to JSON.
  if (stixDisabled.value && exportJob.format === "stix") {
    exportJob.format = "json";
  }
}

async function submit() {
  apiError.value = null;
  await exportsStore
    .create({ ...exportJob })
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
          <option value="attributes">Attributes</option>
          <option value="events">Events</option>
        </select>
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
        >
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="stix" :disabled="stixDisabled">
            STIX 2.1{{ stixDisabled ? " (attributes only)" : "" }}
          </option>
        </select>
        <div class="form-text">
          STIX 2.1 groups matching attributes into events and converts them via
          the misp-stix library.
        </div>
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
