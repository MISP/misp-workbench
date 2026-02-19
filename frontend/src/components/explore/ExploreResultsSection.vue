<script setup>
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faChevronDown,
  faChevronUp,
  faFileDownload,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import Paginate from "vuejs-paginate-next";

defineProps({
  title: { type: String, required: true },
  docs: { type: Object, default: null },
  status: { type: Object, required: true },
  pageCount: { type: Number, default: 0 },
  borderColor: { type: String, default: "#0d6efd" },
});

const emit = defineEmits(["page-change", "download"]);

const isOpen = ref(true);
</script>

<style scoped>
.result-section {
  border-left: 4px solid v-bind(borderColor);
}
</style>

<template>
  <div
    class="result-section card mb-3 col-12 col-md-8 mx-auto"
    v-if="docs?.results || status.error"
  >
    <div class="card-header d-flex justify-content-between align-items-center">
      <div
        class="d-flex align-items-center cursor-pointer"
        @click="isOpen = !isOpen"
      >
        <strong>{{ title }}</strong>
        <span v-if="docs?.total" class="text-muted ms-2">
          ({{ docs.total }})
        </span>
        <span class="ms-2" aria-hidden="true">
          <FontAwesomeIcon
            :icon="isOpen ? faChevronUp : faChevronDown"
            class="ms-1"
          />
        </span>
      </div>

      <div v-if="docs?.total > 0" class="btn-group me-2">
        <button
          type="button"
          class="btn btn-outline-secondary dropdown-toggle"
          data-bs-toggle="dropdown"
          :disabled="status.exporting"
        >
          <span v-if="status.exporting">
            <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
          </span>
          <span v-else class="ms-2">
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
    </div>

    <div v-show="isOpen" class="card-body">
      <div v-if="docs?.results?.length">
        <slot />
        <Paginate
          v-if="pageCount > 1"
          :page-count="pageCount"
          :click-handler="(page) => emit('page-change', page)"
        />
      </div>
      <div v-if="status?.error" class="alert alert-danger mt-3">
        <ApiError :errors="status.error" />
      </div>
      <div v-if="docs && docs.total === 0" class="text-center text-muted mt-3">
        No {{ title.toLowerCase() }} found.
        <div v-if="docs.timed_out" class="alert alert-danger mt-2">
          Request timed out.
        </div>
      </div>
    </div>

    <div
      v-if="isOpen && docs?.total > 0"
      class="card-footer text-muted text-center"
    >
      <div class="mt-2">{{ docs.total }} results · {{ docs.took }}ms</div>
    </div>
  </div>
</template>
