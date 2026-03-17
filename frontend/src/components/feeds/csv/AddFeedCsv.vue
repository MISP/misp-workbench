<script setup>
import { ref, reactive, watch, computed } from "vue";
import CsvPreview from "@/components/feeds/csv/CsvPreview.vue";
import CsvModeSelector from "@/components/feeds/csv/CsvModeSelector.vue";
import CsvAttributeMapping from "@/components/feeds/csv/CsvAttributeMapping.vue";
import CsvObjectMapping from "@/components/feeds/csv/CsvObjectMapping.vue";
import { useFeedsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";

const feedsStore = useFeedsStore();
const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});

const apiError = ref(null);
const csvRows = ref([]);
const loadingPreview = ref(false);

const saved = props.modelValue?.settings?.csvConfig;

const csvConfig = reactive({
  mode: saved?.mode ?? "attribute",
  columns: saved?.columns ?? [],
  delimiter: saved?.delimiter ?? ",",
  header: saved?.header ?? true,
  attribute: {
    value_column: saved?.attribute?.value_column ?? null,
    type: {
      strategy: saved?.attribute?.type?.strategy ?? "fixed",
      value: saved?.attribute?.type?.value ?? null,
      column: saved?.attribute?.type?.column ?? null,
      mappings: saved?.attribute?.type?.mappings ?? [],
    },
    properties: saved?.attribute?.properties ?? {},
  },
  object: {
    template: saved?.object?.template ?? null,
    mappings: saved?.object?.mappings ?? {},
  },
});

watch(
  [csvConfig],
  () => {
    emit("update:modelValue", {
      ...props.modelValue,
      settings: csvConfig ? { csvConfig } : {},
    });
  },
  { deep: true },
);

watch(
  () => props.modelValue.url,
  (newUri, oldUri) => {
    if (newUri && newUri !== oldUri) {
      previewCsvFeed();
    }
  },
  { immediate: true },
);

const columnsComputed = computed(() => {
  if (csvConfig.header && csvRows.value.length > 0) {
    const header = csvRows.value[0];
    return header.map((c) => c);
  }
  return csvRows.value.length > 0
    ? csvRows.value[0].map((_, idx) => `Column ${idx + 1}`)
    : [];
});

const columnsWithIndex = computed(() =>
  csvConfig.columns.map((name, index) => ({
    index,
    name,
  })),
);

watch(
  columnsComputed,
  (newCols) => {
    if (JSON.stringify(newCols) !== JSON.stringify(csvConfig.columns)) {
      csvConfig.columns = [...newCols];
    }
  },
  { immediate: true },
);

function previewCsvFeed() {
  loadingPreview.value = true;
  feedsStore
    .previewCsvFeed(props.modelValue)
    .then((response) => {
      csvRows.value = response.rows || [];
    })
    .catch((error) => (apiError.value = error?.message || String(error)))
    .finally(() => {
      loadingPreview.value = false;
    });
}
</script>
<template>
  <div class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">CSV Preview</h5>
      </div>
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center m-2">
          <div class="d-flex align-items-center gap-3">
            <div class="form-check form-switch mb-0">
              <input
                class="form-check-input"
                type="checkbox"
                id="parseHeader"
                v-model="csvConfig.header"
              />
              <label
                class="form-check-label small text-muted"
                for="parseHeader"
              >
                First row is header
              </label>
            </div>
            <div class="d-flex align-items-center gap-2">
              <select
                id="customDelimiter"
                class="form-select form-select-sm"
                style="width: 140px"
                v-model="csvConfig.delimiter"
              >
                <option value=",">comma (,)</option>
                <option value=";">semicolon (;)</option>
                <option value="|">pipe (|)</option>
                <option value="\t">tab (\t)</option>
                <option value=" ">space ( )</option>
              </select>
              <label
                class="form-check-label small text-muted ms-2"
                for="customDelimiter"
              >
                Delimiter
              </label>
            </div>
          </div>
        </div>
        <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
          {{ apiError }}
        </div>
        <div
          v-if="!csvRows || !csvRows.length"
          class="w-100 alert alert-warning mt-3 mb-3"
        >
          No preview available for this feed. Please check your URI and source
          type.
        </div>
        <div v-if="loadingPreview" class="w-100 alert alert-info mt-3 mb-3">
          Loading preview...
          <FontAwesomeIcon :icon="faSpinner" spin />
        </div>
        <CsvPreview
          :rows="csvConfig.header ? csvRows.slice(1) : csvRows"
          :columns="columnsComputed"
        />
        <small class="text-muted">
          showing first
          {{
            csvConfig.header ? Math.max(0, csvRows.length - 1) : csvRows.length
          }}
          row<span
            v-if="
              (csvConfig.header
                ? Math.max(0, csvRows.length - 1)
                : csvRows.length) !== 1
            "
            >s</span
          >
        </small>
      </div>
    </div>
  </div>
  <CsvModeSelector v-model="csvConfig.mode" />
  <CsvAttributeMapping
    v-if="csvConfig.mode === 'attribute'"
    v-model="csvConfig.attribute"
    :rows="csvConfig.header ? csvRows.slice(1) : csvRows"
    :columns="columnsWithIndex"
  />
  <CsvObjectMapping
    v-else-if="csvConfig.mode === 'object'"
    v-model="csvConfig.object"
    :rows="csvConfig.header ? csvRows.slice(1) : csvRows"
    :columns="columnsWithIndex"
  />
</template>
