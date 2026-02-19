<script setup lang="ts">
import { reactive, watch, computed, ref } from "vue";
import { debounce } from "lodash-es";
import { useEventsStore, useToastsStore } from "@/stores";
import { storeToRefs } from "pinia";
import { ATTRIBUTE_CATEGORIES, ATTRIBUTE_TYPES } from "@/helpers/constants";

const toastsStore = useToastsStore();
const eventsStore = useEventsStore();
const { status } = storeToRefs(eventsStore);

const props = defineProps(["event_uuid"]);
const emit = defineEmits(["event-updated"]);

const modalEl = ref(null);

defineExpose({
  modalEl,
});

const page = reactive({
  current: 1,
  perPage: 10,
});

const totalPages = computed(() =>
  Math.ceil(batchState.lines.length / page.perPage),
);

const paginatedLines = computed(() => {
  const start = (page.current - 1) * page.perPage;
  return batchState.lines.slice(start, start + page.perPage);
});

type ParsedLine = {
  raw: string;
  value: string;
  detected: boolean;
  type: string | null;
  category: string | null;
  overriddenType?: string | null;
  overriddenCategory?: string | null;
  valid: boolean;
  error?: string;
};

const batchState = reactive({
  rawInput: "",
  lines: [] as ParsedLine[],

  overrides: {
    enabled: false,
    type: null as string | null,
    category: null as string | null,
  },

  stats: {
    total: 0,
    valid: 0,
    skipped: 0,
    byType: {} as Record<string, number>,
  },
});

const DETECTORS = [
  {
    type: "sha256",
    category: "Payload delivery",
    regex: /^[a-fA-F0-9]{64}$/,
  },
  {
    type: "sha1",
    category: "Payload delivery",
    regex: /^[a-fA-F0-9]{40}$/,
  },
  {
    type: "md5",
    category: "Payload delivery",
    regex: /^[a-fA-F0-9]{32}$/,
  },
  {
    type: "ip-src",
    category: "Network activity",
    regex: /^(?:\d{1,3}\.){3}\d{1,3}\/(?:[0-9]|[12][0-9]|3[0-2])$/,
  },
  {
    type: "ip-src",
    category: "Network activity",
    regex: /^[0-9a-fA-F:]+\/(?:[0-9]|[1-9][0-9]|1[01][0-9]|12[0-8])$/,
  },
  {
    type: "ip-dst",
    category: "Network activity",
    regex: /^(?:\d{1,3}\.){3}\d{1,3}$/,
  },
  {
    type: "ip-src",
    category: "Network activity",
    regex: /^(?:\d{1,3}\.){3}\d{1,3}$/,
  },
  {
    type: "url",
    category: "Payload delivery",
    regex: /^https?:\/\/\S+/i,
  },
  {
    type: "domain",
    category: "Network activity",
    regex: /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,
  },
];

function detectLine(raw) {
  const value = raw.trim();
  if (!value) return null;

  for (const d of DETECTORS) {
    if (d.regex.test(value)) {
      return {
        detected: true,
        valid: true,
        type: d.type,
        category: d.category,
        value,
        overriddenType: d.type,
        overriddenCategory: d.category,
      };
    }
  }

  return {
    detected: false,
    valid: false,
    value,
    error: "Unknown format",
  };
}

function resolveType(line: ParsedLine) {
  if (line.overriddenType) return line.overriddenType;
  if (batchState.overrides.enabled) return batchState.overrides.type;
  return line.type;
}

function resolveCategory(line: ParsedLine) {
  if (line.overriddenCategory) return line.overriddenCategory;
  if (batchState.overrides.enabled) return batchState.overrides.category;
  return line.category;
}

watch(
  () => batchState.rawInput,
  debounce((input) => {
    const rawLines = input.split(/\r?\n/);

    batchState.lines = rawLines.map(detectLine).filter(Boolean);

    recomputeStats();
  }, 400),
);

function recomputeStats() {
  const stats = {
    total: batchState.lines.length,
    valid: 0,
    skipped: 0,
    byType: {},
  };

  for (const l of batchState.lines) {
    if (!l.valid) {
      stats.skipped++;
      continue;
    }

    stats.valid++;
    stats.byType[l.type] = (stats.byType[l.type] || 0) + 1;
  }

  batchState.stats = stats;
}

function getFinalAttributes() {
  return batchState.lines
    .filter((l) => l.valid)
    .map((l) => ({
      value: l.value,
      type: resolveType(l),
      category: resolveCategory(l),
    }));
}

function onSubmit() {
  const attributes = getFinalAttributes();

  return eventsStore
    .import(props.event_uuid, { attributes: attributes })
    .then((response) => {
      toastsStore.push(response["message"]);
      emit("event-updated", { event_uuid: props.event_uuid });
      resetBatchState();
      modalEl.value?.hide();
    })
    .catch((error) => {
      status.error = error.message || "An error occurred during import.";
      toastsStore.push(
        error.message || "An error occurred during import.",
        "error",
      );
    });
}

function resetBatchState() {
  batchState.rawInput = "";
  batchState.lines = [];
  batchState.overrides.enabled = false;
  batchState.overrides.type = null;
  batchState.overrides.category = null;
  batchState.stats = {
    total: 0,
    valid: 0,
    skipped: 0,
    byType: {},
  };
}
</script>

<template>
  <div
    ref="modalEl"
    :id="'importDataEventModal_' + event_uuid"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="importDataEventModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="importDataEventModal">Import Data</h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
            @click="resetBatchState"
          ></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <h6 class="text-start">Paste indicators (one per line)</h6>
            <textarea
              class="form-control font-monospace"
              rows="8"
              placeholder="Paste indicators (one per line) ..."
              v-model="batchState.rawInput"
            ></textarea>

            <div class="form-text mt-1 d-flex justify-content-between">
              <span>
                {{ batchState.stats.total }} lines ·
                <span class="text-success"
                  >{{ batchState.stats.valid }} valid</span
                >
                <span v-if="batchState.stats.skipped" class="text-danger">
                  · {{ batchState.stats.skipped }} invalid
                </span>
              </span>
              <span class="text-muted"> Detection is automatic </span>
            </div>
          </div>

          <div v-if="batchState.stats.valid" class="mb-3">
            <h6 class="text-start">Detected types</h6>
            <div class="d-flex flex-wrap gap-2">
              <span
                v-for="(count, type) in batchState.stats.byType"
                :key="type"
                class="badge bg-secondary"
              >
                {{ type }} · {{ count }}
              </span>

              <span v-if="batchState.stats.skipped" class="badge bg-danger">
                unknown · {{ batchState.stats.skipped }}
              </span>
            </div>
          </div>

          <div class="card mb-3">
            <div class="card-body">
              <div class="form-check mb-2">
                <input
                  id="enableOverrides"
                  class="form-check-input"
                  type="checkbox"
                  v-model="batchState.overrides.enabled"
                />
                <label class="form-check-label" for="enableOverrides">
                  Override detected type & category
                </label>
              </div>

              <div
                class="row g-2"
                :class="{ 'opacity-50': !batchState.overrides.enabled }"
              >
                <div class="col-md-6">
                  <label class="form-label">Attribute type</label>
                  <select
                    class="form-select"
                    :disabled="!batchState.overrides.enabled"
                    v-model="batchState.overrides.type"
                  >
                    <option disabled value="">Select type</option>
                    <option
                      v-for="type in ATTRIBUTE_TYPES"
                      :key="type"
                      :value="type"
                    >
                      {{ type }}
                    </option>
                  </select>
                </div>

                <div class="col-md-6">
                  <label class="form-label">Category</label>
                  <select
                    class="form-select"
                    :disabled="!batchState.overrides.enabled"
                    v-model="batchState.overrides.category"
                  >
                    <option disabled value="">Select category</option>
                    <option
                      v-for="(cat, name) in ATTRIBUTE_CATEGORIES"
                      :key="name"
                      :value="name"
                    >
                      {{ name }}
                    </option>
                  </select>
                </div>
              </div>

              <div
                v-if="batchState.overrides.enabled"
                class="alert alert-warning mt-3 mb-0 py-2"
              >
                All imported attributes will use the selected type and category.
              </div>
            </div>
          </div>

          <div v-if="batchState.lines.length" class="mb-2">
            <h6 class="text-start">Preview</h6>

            <li
              v-for="(line, index) in paginatedLines"
              :key="index"
              class="list-group-item"
            >
              <div class="input-group mb-3 flex-nowrap">
                <code
                  class="form-control font-monospace text-truncate text-start"
                  style="width: 320px; min-width: 220px; max-width: 420px"
                >
                  {{ line.value }}
                </code>

                <label class="input-group-text">type</label>
                <select
                  class="form-select form-select-sm"
                  v-model="line.overriddenType"
                  :class="{ 'is-invalid': !line.type && !line.overriddenType }"
                  style="width: 180px; min-width: 140px"
                >
                  <option v-for="t in ATTRIBUTE_TYPES" :key="t" :value="t">
                    {{ t }}
                  </option>
                </select>

                <label class="input-group-text">category</label>
                <select
                  class="form-select form-select-sm"
                  v-model="line.overriddenCategory"
                  :class="{
                    'is-invalid': !line.category && !line.overriddenCategory,
                  }"
                  style="width: 180px; min-width: 140px"
                >
                  <option
                    v-for="(c, name) in ATTRIBUTE_CATEGORIES"
                    :key="name"
                    :value="name"
                  >
                    {{ name }}
                  </option>
                </select>
              </div>
            </li>
            <nav v-if="totalPages > 1" class="mt-2">
              <ul class="pagination pagination-sm justify-content-center">
                <li class="page-item" :class="{ disabled: page.current === 1 }">
                  <button class="page-link" @click="page.current--">
                    Prev
                  </button>
                </li>

                <li class="page-item disabled">
                  <span class="page-link">
                    {{ page.current }} / {{ totalPages }}
                  </span>
                </li>

                <li
                  class="page-item"
                  :class="{ disabled: page.current === totalPages }"
                >
                  <button class="page-link" @click="page.current++">
                    Next
                  </button>
                </li>
              </ul>
            </nav>
          </div>
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
            @click="resetBatchState"
          >
            Discard
          </button>
          <button
            type="submit"
            @click="onSubmit"
            class="btn btn-primary"
            :class="{ disabled: status.importing }"
          >
            <span v-if="status.importing">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.importing">Import</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
