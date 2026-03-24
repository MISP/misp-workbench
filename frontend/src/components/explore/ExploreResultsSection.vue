<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faFileDownload,
  faSpinner,
  faSortUp,
  faSortDown,
} from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import Paginate from "vuejs-paginate-next";

const props = defineProps({
  title: { type: String, required: true },
  docs: { type: Object, default: null },
  status: { type: Object, required: true },
  pageCount: { type: Number, default: 0 },
  sortBy: { type: String, default: "@timestamp" },
  sortOrder: { type: String, default: "desc" },
});

const emit = defineEmits(["page-change", "download", "sort-change"]);

const SORT_FIELDS = [
  { value: "_score", label: "Relevance" },
  { value: "@timestamp", label: "Date" },
];

function setSortBy(value) {
  emit("sort-change", { sortBy: value, sortOrder: props.sortOrder });
}

function toggleSortOrder() {
  emit("sort-change", {
    sortBy: props.sortBy,
    sortOrder: props.sortOrder === "asc" ? "desc" : "asc",
  });
}
</script>

<template>
  <div
    class="result-section mb-3 col-12 col-md-10 mx-auto"
    v-if="docs?.results || status.error"
  >
    <div class="d-flex justify-content-end gap-2">
      <div class="btn-group mt-2 mb-2">
        <slot name="header-extra" />
        <button
          v-if="docs?.total > 0"
          type="button"
          class="btn btn-sm btn-outline-info dropdown-toggle"
          data-bs-toggle="dropdown"
          :disabled="status.exporting"
        >
          <span v-if="status.exporting">
            <FontAwesomeIcon :icon="faSpinner" spin />
          </span>
          <span v-else>
            <FontAwesomeIcon :icon="faFileDownload" /> Download
          </span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li>
            <button class="dropdown-item" @click="emit('download', 'json')">
              All results (JSON)
            </button>
          </li>
        </ul>
      </div>
      <div class="btn-group mt-2 mb-2">
        <button
          type="button"
          class="btn btn-sm btn-outline-secondary"
          @click="toggleSortOrder"
        >
          <FontAwesomeIcon
            :icon="sortOrder === 'asc' ? faSortUp : faSortDown"
          />
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline-secondary dropdown-toggle"
          data-bs-toggle="dropdown"
        >
          {{ SORT_FIELDS.find((f) => f.value === sortBy)?.label }}
        </button>
        <ul class="dropdown-menu">
          <li v-for="field in SORT_FIELDS" :key="field.value">
            <button
              class="dropdown-item"
              :class="{ active: sortBy === field.value }"
              @click="setSortBy(field.value)"
            >
              {{ field.label }}
            </button>
          </li>
        </ul>
      </div>
    </div>
    <slot />
    <div class="d-flex justify-content-center">
      <div v-if="status?.error" class="alert alert-danger mt-3">
        <ApiError :errors="status.error" />
      </div>
      <div
        v-if="docs && docs.total === 0"
        class="text-center text-muted fst-italic mt-3"
      >
        No {{ title.toLowerCase() }} found.
        <div v-if="docs.timed_out" class="alert alert-danger mt-3">
          Request timed out.
        </div>
      </div>
    </div>
    <Paginate
      v-if="pageCount > 1"
      :page-count="pageCount"
      :click-handler="(page) => emit('page-change', page)"
    />
  </div>
</template>
