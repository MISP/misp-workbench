<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faFileDownload, faSpinner } from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import Paginate from "vuejs-paginate-next";

defineProps({
  title: { type: String, required: true },
  docs: { type: Object, default: null },
  status: { type: Object, required: true },
  pageCount: { type: Number, default: 0 },
});

const emit = defineEmits(["page-change", "download"]);
</script>

<template>
  <div
    class="result-section mb-3 col-12 col-md-10 mx-auto"
    v-if="docs?.results || status.error"
  >
    <div v-if="docs?.total > 0" class="d-flex justify-content-end">
      <div class="btn-group mt-2 mb-2">
        <slot name="header-extra" />
        <button
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

        <div v-if="docs?.total > 0" class="card-footer text-muted text-center">
          <div class="mt-2">{{ docs.total }} results · {{ docs.took }}ms</div>
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
