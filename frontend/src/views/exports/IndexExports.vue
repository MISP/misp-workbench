<script setup>
import { ref, computed, onUnmounted } from "vue";
import { storeToRefs } from "pinia";
import { useExportsStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ExportScheduleModal from "@/components/exports/ExportScheduleModal.vue";
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
const scheduleModalItem = ref(null);

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function pad2(v) {
  return String(v).padStart(2, "0");
}

// Human-readable summary of a stored crontab schedule.
function scheduleSummary(s) {
  if (!s) return null;
  const time = `${pad2(s.hour === "*" ? 0 : s.hour)}:${pad2(
    s.minute === "*" ? 0 : s.minute,
  )}`;
  if (s.day_of_week !== "*" && s.day_of_month === "*") {
    const d = DAY_LABELS[parseInt(s.day_of_week, 10)] ?? s.day_of_week;
    return `Weekly · ${d} ${time}`;
  }
  if (s.day_of_month !== "*") return `Monthly · day ${s.day_of_month} ${time}`;
  if (s.hour !== "*") return `Daily · ${time}`;
  if (s.minute !== "*") return `Hourly · :${pad2(s.minute)}`;
  return "Custom";
}

async function toggleScheduleEnabled(item) {
  try {
    await exportsStore.updateSchedule(item.id, {
      schedule_enabled: !item.schedule_enabled,
    });
    await exportsStore.getAll();
  } catch (err) {
    toastsStore.push(err?.message || "Failed to update schedule.", "danger");
  }
}

async function unschedule(item) {
  if (!window.confirm(`Remove the schedule for "${item.name}"?`)) return;
  try {
    await exportsStore.updateSchedule(item.id, {
      schedule: null,
      schedule_enabled: false,
    });
    toastsStore.push(`Schedule removed for "${item.name}".`, "success");
    await exportsStore.getAll();
  } catch (err) {
    toastsStore.push(err?.message || "Failed to remove schedule.", "danger");
  }
}

async function onScheduleSaved() {
  scheduleModalItem.value = null;
  await exportsStore.getAll();
}

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
          <th v-if="!$isMobile">schedule</th>
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
          <td v-if="!$isMobile" class="small">
            <template v-if="item.schedule">
              <span
                class="badge"
                :class="item.schedule_enabled ? 'bg-info' : 'bg-secondary'"
                :title="item.schedule_enabled ? 'Active' : 'Paused'"
              >
                {{ scheduleSummary(item.schedule) }}
                <span v-if="!item.schedule_enabled">(paused)</span>
              </span>
              <div v-if="item.last_run_at" class="text-muted">
                last run {{ dayjs.utc(item.last_run_at).local().fromNow() }}
              </div>
            </template>
            <span v-else class="text-muted">—</span>
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
            <template v-if="canCreate">
              <button
                v-if="item.schedule"
                class="btn btn-outline-secondary btn-sm me-1"
                :title="
                  item.schedule_enabled ? 'Pause schedule' : 'Resume schedule'
                "
                @click="toggleScheduleEnabled(item)"
              >
                {{ item.schedule_enabled ? "Pause" : "Resume" }}
              </button>
              <button
                class="btn btn-outline-secondary btn-sm me-1"
                :title="item.schedule ? 'Edit schedule' : 'Add schedule'"
                @click="scheduleModalItem = item"
              >
                {{ item.schedule ? "Edit schedule" : "Schedule" }}
              </button>
              <button
                v-if="item.schedule"
                class="btn btn-outline-warning btn-sm me-1"
                title="Remove schedule"
                @click="unschedule(item)"
              >
                Unschedule
              </button>
            </template>
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

  <ExportScheduleModal
    v-if="scheduleModalItem"
    :export-item="scheduleModalItem"
    @saved="onScheduleSaved"
    @close="scheduleModalItem = null"
  />
</template>
