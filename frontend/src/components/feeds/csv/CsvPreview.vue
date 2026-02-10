<script setup>
import { computed, ref, watch, onMounted } from "vue";

const props = defineProps({
  columns: {
    type: Array,
    default: () => [],
  },
  rows: {
    type: Array,
    required: true,
  },
  maxRows: {
    type: Number,
    default: 5,
  },
});

const emit = defineEmits(["update:columns"]);

// whether to treat the first row as header (preview only)
const parseHeader = ref(true);

function cleanCell(raw) {
  if (raw === null || raw === undefined) return "";
  let s = String(raw);
  // trim whitespace
  s = s.trim();
  // remove surrounding quotes if present
  s = s.replace(/^"|"$/g, "");
  return s;
}

const rowsSource = computed(() => {
  // props.rows is an array of arrays (preview)
  if (!Array.isArray(props.rows)) return [];
  return props.rows;
});

const columnsComputed = computed(() => {
  if (parseHeader.value && rowsSource.value.length > 0) {
    const header = rowsSource.value[0];
    return header.map((c) => cleanCell(c));
  }
  return rowsSource.value.length > 0
    ? rowsSource.value[0].map((_, idx) => `Column ${idx + 1}`)
    : [];
});

const dataRows = computed(() => {
  if (parseHeader.value && rowsSource.value.length > 1) {
    return rowsSource.value.slice(1);
  }
  if (parseHeader.value) return [];
  return rowsSource.value;
});

const displayedRows = computed(() => {
  return dataRows.value.slice(0, props.maxRows);
});

watch(parseHeader, () => {
  emit("update:columns", columnsComputed.value || []);
});

onMounted(() => {
  emit("update:columns", columnsComputed.value || []);
});

function formatValue(value) {
  if (value === null || value === undefined) {
    return "";
  }

  const str = String(value);
  return str.length > 50 ? str.slice(0, 47) + "…" : str;
}
</script>
<style scoped>
.csv-preview-table {
  max-height: 240px;
  overflow: auto;
}

td.text-truncate {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<template>
  <div class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">CSV Preview</h5>
      </div>
      <div class="card-body">
        <div class="csv-preview">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="d-flex align-items-center gap-3">
              <small class="text-muted">
                Showing first {{ displayedRows.length }} row<span
                  v-if="displayedRows.length !== 1"
                  >s</span
                >
              </small>
              <div class="form-check form-switch mb-0">
                <input
                  class="form-check-input"
                  type="checkbox"
                  id="parseHeader"
                  v-model="parseHeader"
                />
                <label
                  class="form-check-label small text-muted"
                  for="parseHeader"
                  >First row is header</label
                >
              </div>
            </div>
          </div>

          <div class="table-responsive csv-preview-table">
            <table class="table table-sm table-bordered align-middle mb-0">
              <thead class="table-secondary">
                <tr>
                  <th
                    v-for="(col, idx) in columnsComputed"
                    :key="idx"
                    class="text-nowrap"
                  >
                    {{ col }}
                  </th>
                </tr>
              </thead>

              <tbody>
                <tr v-for="(row, index) in displayedRows" :key="index">
                  <td
                    v-for="(col, cidx) in columnsComputed"
                    :key="cidx"
                    class="text-truncate"
                    :title="row[cidx]"
                  >
                    {{ formatValue(cleanCell(row[cidx])) }}
                  </td>
                </tr>

                <tr v-if="!displayedRows.length">
                  <td
                    :colspan="columnsComputed.length || columns.length"
                    class="text-center text-muted py-3"
                  >
                    No data to preview
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
