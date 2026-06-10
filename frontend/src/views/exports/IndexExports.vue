<script setup>
import { ref, computed, onUnmounted } from "vue";
import { storeToRefs } from "pinia";
import { useExportsStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { authHelper } from "@/helpers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const exportsStore = useExportsStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { exports, status } = storeToRefs(exportsStore);
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "exports:create"),
);
const canDelete = computed(() =>
  authHelper.hasScope(scopes.value, "exports:delete"),
);

const STATUS_BADGE = {
  queued: "bg-secondary",
  running: "bg-info",
  completed: "bg-success",
  failed: "bg-danger",
};

function formatBytes(bytes) {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const downloadingId = ref(null);

async function downloadExport(item) {
  downloadingId.value = item.id;
  try {
    await exportsStore.download(item);
  } catch (err) {
    toastsStore.push(err?.message || "Download failed.", "danger");
  } finally {
    downloadingId.value = null;
  }
}

async function deleteExport(item) {
  if (!window.confirm(`Delete export "${item.name}"?`)) return;
  await exportsStore.delete(item.id);
  toastsStore.push(`Export "${item.name}" deleted.`, "success");
  exportsStore.getAll();
}

// Poll while any export is still queued/running so the table updates without
// a manual refresh; stop once everything has settled.
let pollTimer = null;

function hasPending() {
  return (exports.value?.items || []).some(
    (e) => e.status === "queued" || e.status === "running",
  );
}

function schedulePoll() {
  clearTimeout(pollTimer);
  if (hasPending()) {
    pollTimer = setTimeout(async () => {
      await exportsStore.getAll();
      schedulePoll();
    }, 3000);
  }
}

exportsStore.getAll().then(schedulePoll);

onUnmounted(() => clearTimeout(pollTimer));
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h4 class="mb-0">Exports</h4>
    <RouterLink
      v-if="canCreate"
      to="/exports/add"
      class="btn btn-primary btn-sm"
    >
      + New Export
    </RouterLink>
  </div>

  <Spinner v-if="status.loading && !exports" />

  <div
    v-else-if="exports && exports.items && exports.items.length === 0"
    class="text-muted"
  >
    No exports yet.<template v-if="canCreate">
      Create one to get started.</template
    >
  </div>

  <div v-else-if="exports && exports.items" class="table-responsive">
    <table class="table table-striped text-start align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th v-if="!$isMobile">target</th>
          <th v-if="!$isMobile">format</th>
          <th v-if="!$isMobile">records</th>
          <th v-if="!$isMobile">size</th>
          <th v-if="!$isMobile">created</th>
          <th class="text-end">status</th>
          <th class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in exports.items" :key="item.id">
          <td>
            <span class="fw-semibold">{{ item.name }}</span>
            <div
              class="text-muted small text-truncate font-monospace"
              style="max-width: 320px"
              :title="item.query"
            >
              {{ item.query }}
            </div>
            <div
              v-if="item.status === 'failed' && item.error"
              class="text-danger small text-truncate"
              style="max-width: 320px"
              :title="item.error"
            >
              {{ item.error }}
            </div>
          </td>
          <td v-if="!$isMobile">
            <span class="badge bg-secondary">{{ item.index_target }}</span>
          </td>
          <td v-if="!$isMobile">
            <span class="badge bg-light text-dark text-uppercase">{{
              item.format
            }}</span>
          </td>
          <td v-if="!$isMobile" class="text-muted small">
            {{ item.record_count ?? "—" }}
          </td>
          <td v-if="!$isMobile" class="text-muted small">
            {{ formatBytes(item.file_size) }}
          </td>
          <td v-if="!$isMobile" class="text-muted small">
            {{ dayjs.utc(item.created_at).local().fromNow() }}
          </td>
          <td class="text-end">
            <span
              class="badge"
              :class="STATUS_BADGE[item.status] || 'bg-secondary'"
            >
              {{ item.status }}
            </span>
          </td>
          <td class="text-end">
            <button
              v-if="item.status === 'completed'"
              class="btn btn-outline-primary btn-sm me-1"
              :disabled="downloadingId === item.id"
              @click="downloadExport(item)"
            >
              {{ downloadingId === item.id ? "…" : "Download" }}
            </button>
            <button
              v-if="canDelete"
              class="btn btn-outline-danger btn-sm"
              @click="deleteExport(item)"
            >
              Delete
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
