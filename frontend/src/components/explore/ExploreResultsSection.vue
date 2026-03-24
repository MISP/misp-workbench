<script setup>
import { ref, computed, watch, watchEffect } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faFileDownload,
  faSpinner,
  faSortUp,
  faSortDown,
  faFilter,
} from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import Paginate from "vuejs-paginate-next";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import AttributeTypeMultiSelect from "@/components/enums/AttributeTypeMultiSelect.vue";
import OrganisationMultiSelect from "@/components/organisations/OrganisationMultiSelect.vue";

const props = defineProps({
  title: { type: String, required: true },
  docs: { type: Object, default: null },
  status: { type: Object, required: true },
  pageCount: { type: Number, default: 0 },
  sortBy: { type: String, default: "@timestamp" },
  sortOrder: { type: String, default: "desc" },
  filterFields: { type: Array, default: () => ["organisation", "tags"] },
  visible: { type: Boolean, default: true },
});

const emit = defineEmits([
  "page-change",
  "download",
  "sort-change",
  "filter-change",
]);

const SORT_FIELDS = [
  { value: "_score", label: "Relevance" },
  { value: "@timestamp", label: "Date" },
];

const FILTER_LABELS = {
  organisation: "Organisation",
  tags: "Tags",
  type: "Type",
};

const selectedOrgNames = ref([]);
const selectedTagNames = ref([]);
const selectedTypeNames = ref([]);

const hasBeenVisible = ref(props.visible);
watch(
  () => props.visible,
  (v) => {
    if (v) hasBeenVisible.value = true;
  },
);

const filterButtonEl = ref(null);

function onFilterHide(event) {
  if (document.querySelector(".ts-wrapper.is-open")) {
    event.preventDefault();
  }
}

watchEffect((onCleanup) => {
  const el = filterButtonEl.value;
  if (!el) return;
  el.addEventListener("hide.bs.dropdown", onFilterHide);
  onCleanup(() => el.removeEventListener("hide.bs.dropdown", onFilterHide));
});

const totalFilterCount = computed(
  () =>
    selectedOrgNames.value.length +
    selectedTagNames.value.length +
    selectedTypeNames.value.length,
);

function emitFilters() {
  const orgFilters = selectedOrgNames.value.map((n) => ({
    key: "organisation",
    field: "organisation.name",
    value: n,
  }));
  const tagFilters = selectedTagNames.value.map((n) => ({
    key: "tags",
    field: "tags.name",
    value: n,
  }));
  const typeFilters = selectedTypeNames.value.map((n) => ({
    key: "type",
    field: "type",
    value: n,
  }));
  emit("filter-change", [...orgFilters, ...tagFilters, ...typeFilters]);
}

function setSortBy(value) {
  emit("sort-change", { sortBy: value, sortOrder: props.sortOrder });
}

function toggleSortOrder() {
  emit("sort-change", {
    sortBy: props.sortBy,
    sortOrder: props.sortOrder === "asc" ? "desc" : "asc",
  });
}

function onOrgsChanged(names) {
  selectedOrgNames.value = names;
  emitFilters();
}

function onTagsChanged(names) {
  selectedTagNames.value = names;
  emitFilters();
}

function onTypesChanged(types) {
  selectedTypeNames.value = types;
  emitFilters();
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
          class="btn btn-sm btn-outline-info"
          @click="toggleSortOrder"
        >
          <FontAwesomeIcon
            :icon="sortOrder === 'asc' ? faSortUp : faSortDown"
          />
        </button>
        <button
          type="button"
          class="btn btn-sm btn-outline-info dropdown-toggle"
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
      <div class="btn-group mt-2 mb-2">
        <button
          ref="filterButtonEl"
          type="button"
          class="btn btn-sm btn-outline-info dropdown-toggle position-relative"
          :class="{ active: totalFilterCount > 0 }"
          data-bs-toggle="dropdown"
          data-bs-auto-close="outside"
        >
          <FontAwesomeIcon :icon="faFilter" />
          <span
            v-if="totalFilterCount > 0"
            class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-primary"
            style="font-size: 0.6em"
            :title="`${totalFilterCount} filter${totalFilterCount > 1 ? 's' : ''} active`"
          >
            {{ totalFilterCount }}
          </span>
        </button>
        <div class="dropdown-menu p-2" style="min-width: 280px" @click.stop>
          <template v-if="hasBeenVisible">
            <div v-for="key in filterFields" :key="key" class="mb-2">
              <label class="form-label small fw-semibold mb-1">
                {{ FILTER_LABELS[key] }}
              </label>
              <OrganisationMultiSelect
                v-if="key === 'organisation'"
                :selected="selectedOrgNames"
                @update:selected="onOrgsChanged"
              />
              <TagsSelect
                v-else-if="key === 'tags'"
                model-class="event"
                :selected-tags="[]"
                :persist="false"
                @update:selected-tags="onTagsChanged"
              />
              <AttributeTypeMultiSelect
                v-else-if="key === 'type'"
                :selected="selectedTypeNames"
                @update:selected="onTypesChanged"
              />
            </div>
          </template>
        </div>
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
