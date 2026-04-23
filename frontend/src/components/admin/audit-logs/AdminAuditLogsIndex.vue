<script setup>
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import Paginate from "vuejs-paginate-next";
import { useAuditLogsStore, useUsersStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const PAGE_SIZE = 25;

const auditLogsStore = useAuditLogsStore();
const usersStore = useUsersStore();

const { auditLogs, status } = storeToRefs(auditLogsStore);
const { users } = storeToRefs(usersStore);

const filters = ref({
  action: "",
  resource_type: "",
  resource_id: "",
  actor_user_id: "",
  actor_type: "",
  date_from: "",
  date_to: "",
});

const expandedRow = ref(null);

const usersById = computed(() => {
  const map = {};
  const list = Array.isArray(users.value) ? users.value : [];
  for (const u of list) map[u.id] = u;
  return map;
});

const pageCount = computed(() =>
  auditLogs.value?.total ? Math.ceil(auditLogs.value.total / PAGE_SIZE) : 0,
);

function buildParams(page = 1) {
  const params = { page, size: PAGE_SIZE };
  for (const [k, v] of Object.entries(filters.value)) {
    if (v !== "" && v !== null && v !== undefined) params[k] = v;
  }
  return params;
}

function load(page = 1) {
  return auditLogsStore.getAll(buildParams(page));
}

function applyFilters() {
  load(1);
}

function clearFilters() {
  filters.value = {
    action: "",
    resource_type: "",
    resource_id: "",
    actor_user_id: "",
    actor_type: "",
    date_from: "",
    date_to: "",
  };
  load(1);
}

function onPageChange(page) {
  load(page);
}

function toggleRow(id) {
  expandedRow.value = expandedRow.value === id ? null : id;
}

function actorLabel(entry) {
  if (entry.actor_type === "system") return "system";
  if (entry.actor_email) return entry.actor_email;
  if (entry.actor_user_id) {
    const u = usersById.value[entry.actor_user_id];
    if (u?.email) return u.email;
    return `user #${entry.actor_user_id}`;
  }
  return "-";
}

function resourceLabel(entry) {
  if (entry.resource_id) return `${entry.resource_type}#${entry.resource_id}`;
  return entry.resource_type;
}

function formatDate(d) {
  if (!d) return "-";
  try {
    return new Date(d).toLocaleString();
  } catch {
    return d;
  }
}

function actorBadgeClass(actorType) {
  switch (actorType) {
    case "system":
      return "bg-info text-dark";
    case "api_key":
      return "bg-secondary";
    default:
      return "bg-primary";
  }
}

onMounted(async () => {
  usersStore.getAll();
  load(1);
});
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h4 class="mb-0">Audit logs</h4>
  </div>

  <div class="alert alert-secondary small">
    Append-only record of security-relevant actions: API key lifecycle, admin
    operations, logins. Each entry captures who acted, from where, and what they
    changed.
  </div>

  <form class="row g-2 align-items-end mb-3" @submit.prevent="applyFilters">
    <div class="col-md-3">
      <label class="form-label small text-muted mb-1">action (prefix)</label>
      <input
        v-model="filters.action"
        type="text"
        class="form-control form-control-sm"
        placeholder="e.g. api_key."
      />
    </div>
    <div class="col-md-2">
      <label class="form-label small text-muted mb-1">resource type</label>
      <input
        v-model="filters.resource_type"
        type="text"
        class="form-control form-control-sm"
        placeholder="e.g. api_key"
      />
    </div>
    <div class="col-md-2">
      <label class="form-label small text-muted mb-1">resource id</label>
      <input
        v-model="filters.resource_id"
        type="number"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-md-3">
      <label class="form-label small text-muted mb-1">actor user</label>
      <select
        v-model="filters.actor_user_id"
        class="form-select form-select-sm"
      >
        <option value="">any user</option>
        <option v-for="u in users" :key="u.id" :value="u.id">
          {{ u.email }}
        </option>
      </select>
    </div>
    <div class="col-md-2">
      <label class="form-label small text-muted mb-1">actor type</label>
      <select v-model="filters.actor_type" class="form-select form-select-sm">
        <option value="">any</option>
        <option value="user">user</option>
        <option value="api_key">api_key</option>
        <option value="system">system</option>
      </select>
    </div>
    <div class="col-md-3">
      <label class="form-label small text-muted mb-1">from</label>
      <input
        v-model="filters.date_from"
        type="datetime-local"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-md-3">
      <label class="form-label small text-muted mb-1">to</label>
      <input
        v-model="filters.date_to"
        type="datetime-local"
        class="form-control form-control-sm"
      />
    </div>
    <div class="col-md-auto">
      <button type="submit" class="btn btn-outline-primary btn-sm">
        apply
      </button>
      <button
        type="button"
        class="btn btn-outline-secondary btn-sm ms-2"
        @click="clearFilters"
      >
        clear
      </button>
    </div>
  </form>

  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading audit logs: {{ status.error }}
  </div>

  <div v-if="!status.loading" class="table-responsive-sm">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th style="width: 13rem">timestamp</th>
          <th>actor</th>
          <th>action</th>
          <th>resource</th>
          <th>IP</th>
          <th class="text-end">details</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!auditLogs.items?.length">
          <td colspan="6" class="text-center text-muted fst-italic">
            no audit log entries match the current filter
          </td>
        </tr>
        <template v-for="entry in auditLogs.items" :key="entry.id">
          <tr>
            <td>
              <div class="small">{{ formatDate(entry.created_at) }}</div>
            </td>
            <td>
              <div class="d-flex align-items-center gap-2">
                <span
                  class="badge"
                  :class="actorBadgeClass(entry.actor_type)"
                  :title="`actor_type = ${entry.actor_type}`"
                >
                  {{ entry.actor_type }}
                </span>
                <code class="small">{{ actorLabel(entry) }}</code>
              </div>
            </td>
            <td>
              <code>{{ entry.action }}</code>
            </td>
            <td>
              <code class="small">{{ resourceLabel(entry) }}</code>
            </td>
            <td>
              <code v-if="entry.ip_address" class="small">{{
                entry.ip_address
              }}</code>
              <span v-else class="text-muted">-</span>
            </td>
            <td class="text-end">
              <button
                v-if="entry.metadata || entry.user_agent"
                class="btn btn-outline-secondary btn-sm"
                @click="toggleRow(entry.id)"
              >
                {{ expandedRow === entry.id ? "hide" : "show" }}
              </button>
            </td>
          </tr>
          <tr v-if="expandedRow === entry.id">
            <td colspan="6" class="bg-body-tertiary">
              <div v-if="entry.user_agent" class="small mb-2">
                <span class="text-muted me-2">user agent:</span>
                <code>{{ entry.user_agent }}</code>
              </div>
              <div v-if="entry.metadata">
                <div class="small text-muted mb-1">metadata:</div>
                <pre class="small mb-0">{{
                  JSON.stringify(entry.metadata, null, 2)
                }}</pre>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>

    <div class="d-flex justify-content-between align-items-center">
      <div class="small text-muted">
        {{ auditLogs.total || 0 }} total entries
      </div>
      <Paginate
        v-if="pageCount > 1"
        :page-count="pageCount"
        :click-handler="onPageChange"
      />
    </div>
  </div>
</template>
