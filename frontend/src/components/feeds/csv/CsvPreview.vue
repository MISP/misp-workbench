<script setup>
defineProps({
  columns: {
    type: Array,
    default: () => [],
  },
  rows: {
    type: Array,
    required: true,
  },
  preview: {
    type: Array,
    default: () => [],
  },
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
td.text-truncate {
  max-width: 200px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>

<template>
  <div class="csv-preview">
    <div class="table-responsive">
      <table class="table table-sm table-bordered align-middle mb-0">
        <thead class="table-secondary">
          <tr>
            <th style="width: 30px">#</th>
            <th v-for="(col, idx) in columns" :key="idx" class="text-nowrap">
              {{ col }}
            </th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(row, index) in rows" :key="index">
            <td>{{ index + 1 }}</td>
            <td
              v-for="(col, cidx) in columns"
              :key="cidx"
              class="text-truncate"
              :title="row[cidx]"
            >
              {{ formatValue(row[cidx]) }}
            </td>
          </tr>

          <tr v-if="!rows.length">
            <td
              :colspan="columns.length || columns.length"
              class="text-center text-muted py-3"
            >
              No data to preview
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="preview.length > 0" class="mt-4">
        <div
          v-for="(attribute, idx) in preview"
          :key="attribute.type"
          class="mb-2"
        >
          <table
            class="table table-bordered m-0 alert"
            :class="attribute.error ? 'alert-danger' : 'alert-success'"
          >
            <tbody>
              <tr>
                <td colspan="2" v-if="attribute.error">
                  <div class="text-danger small">
                    {{ attribute.error }}
                  </div>
                </td>
              </tr>
              <tr v-if="attribute.value">
                <td colspan="2">
                  <div class="text-truncate" style="max-width: 300px">
                    <span class="text-muted small">#{{ idx + 1 }}</span>
                    <span v-if="attribute.type" class="badge bg-primary ms-2">{{
                      attribute.type
                    }}</span>
                    <code class="ms-2">{{ attribute.value }}</code>
                  </div>
                </td>
              </tr>
              <tr v-if="attribute.tags?.length">
                <th style="width: 100px">tags</th>
                <td>
                  <span
                    v-for="(tag, tidx) in attribute.tags"
                    :key="tidx"
                    class="badge bg-info ms-2"
                    >{{ tag }}</span
                  >
                </td>
              </tr>
              <tr v-if="attribute.comment" style="width: 50px">
                <th style="width: 100px">comment</th>
                <td>{{ attribute.comment || "" }}</td>
              </tr>
              <tr v-if="attribute.timestamp">
                <th style="width: 100px">timestamp</th>
                <td>{{ attribute.timestamp }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>
