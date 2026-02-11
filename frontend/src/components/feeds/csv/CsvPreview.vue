<script setup>
import { computed } from "vue";

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

const displayedRows = computed(() => {
  return props.rows.slice(0, props.maxRows);
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
  <div class="csv-preview">
    <div class="table-responsive csv-preview-table">
      <table class="table table-sm table-bordered align-middle mb-0">
        <thead class="table-secondary">
          <tr>
            <th v-for="(col, idx) in columns" :key="idx" class="text-nowrap">
              {{ col }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(row, index) in displayedRows" :key="index">
            <td
              v-for="(col, cidx) in columns"
              :key="cidx"
              class="text-truncate"
              :title="row[cidx]"
            >
              {{ formatValue(row[cidx]) }}
            </td>
          </tr>

          <tr v-if="!displayedRows.length">
            <td
              :colspan="columns.length || columns.length"
              class="text-center text-muted py-3"
            >
              No data to preview
            </td>
          </tr>
        </tbody>
      </table>
      <small class="text-muted">
        showing first {{ displayedRows.length }} row<span
          v-if="displayedRows.length !== 1"
          >s</span
        >
      </small>
    </div>
  </div>
</template>
