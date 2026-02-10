<script setup>
import { ref, reactive, watch } from "vue";
import CsvPreview from "@/components/feeds/csv/CsvPreview.vue";
import CsvModeSelector from "@/components/feeds/csv/CsvModeSelector.vue";
import CsvAttributeMapping from "@/components/feeds/csv/CsvAttributeMapping.vue";
import { useFeedsStore } from "@/stores";

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

const csvConfig = reactive({
  mode: "attribute",
  columns: [],
  attribute: {
    value_column: null,
    type: {
      strategy: "fixed",
      value: null,
      column: null,
      mappings: [],
    },
    properties: {},
  },
  object: {
    template: null,
    mappings: {},
  },
});

watch(
  [csvConfig],
  () => {
    emit("update:modelValue", {
      typeConfig: { settings: csvConfig ? { csvConfig } : {} },
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
);

function previewCsvFeed() {
  feedsStore
    .previewCsvFeed({
      url: props.modelValue.url,
      mode: props.modelValue.input_source,
    })
    .then((response) => {
      csvRows.value = response.preview;
    })
    .catch((error) => (apiError.value = error?.message || String(error)));
}
</script>
<template>
  <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
    {{ apiError }}
  </div>
  <div v-else-if="!csvRows.length" class="w-100 alert alert-warning mt-3 mb-3">
    No preview available for this feed. Please check your URI and source type.
  </div>
  <div v-else>
    <CsvPreview :rows="csvRows" v-model:columns="csvConfig.columns" />
  </div>
  <CsvModeSelector v-model="csvConfig.mode" />
  <CsvAttributeMapping
    v-if="csvConfig.mode === 'attribute'"
    v-model="csvConfig.attribute"
    :rows="csvRows"
    :columns="csvConfig.columns"
  />
</template>
