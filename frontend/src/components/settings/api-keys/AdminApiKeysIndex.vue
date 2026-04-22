<script setup>
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useApiKeysStore, useUsersStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faBan,
  faCheck,
  faTriangleExclamation,
} from "@fortawesome/free-solid-svg-icons";

const apiKeysStore = useApiKeysStore();
const usersStore = useUsersStore();
const toastsStore = useToastsStore();

const { adminApiKeys, adminStatus } = storeToRefs(apiKeysStore);
const { users } = storeToRefs(usersStore);

const userFilter = ref("");

const usersById = computed(() => {
  const map = {};
  const list = Array.isArray(users.value) ? users.value : [];
  for (const u of list) map[u.id] = u;
  return map;
});

onMounted(async () => {
  usersStore.getAll();
  await apiKeysStore.adminGetAll();
});

async function applyFilter() {
  const id = userFilter.value ? Number(userFilter.value) : null;
  await apiKeysStore.adminGetAll(id);
}

async function clearFilter() {
  userFilter.value = "";
  await apiKeysStore.adminGetAll();
}

async function toggleDisabled(key) {
  const next = !key.admin_disabled;
  const owner = ownerLabel(key);
  if (
    !confirm(
      next
        ? `Lock API key "${key.name}" owned by ${owner}? It will stop authenticating and cannot be re-enabled or deleted by the owner.`
        : `Unlock API key "${key.name}" owned by ${owner}? It will authenticate again unless the owner has also disabled it.`,
    )
  )
    return;
  try {
    await apiKeysStore.adminSetDisabled(key.id, next);
    toastsStore.push(`API key ${next ? "locked" : "unlocked"}.`, "success");
  } catch (err) {
    toastsStore.push(`Update failed: ${err?.message || err}`, "error");
  }
}

async function remove(key) {
  const owner = ownerLabel(key);
  if (
    !confirm(
      `Delete API key "${key.name}" owned by ${owner}? This cannot be undone.`,
    )
  )
    return;
  try {
    await apiKeysStore.adminDelete(key.id);
    toastsStore.push("API key deleted.", "success");
  } catch (err) {
    toastsStore.push(`Delete failed: ${err?.message || err}`, "error");
  }
}

function ownerLabel(key) {
  const u = usersById.value[key.user_id];
  return u?.email || `user #${key.user_id}`;
}

function formatDate(d) {
  if (!d) return "-";
  try {
    return new Date(d).toLocaleString();
  } catch {
    return d;
  }
}

function isExpired(d) {
  if (!d) return false;
  return new Date(d) < new Date();
}
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h4 class="mb-0">API keys (admin)</h4>
  </div>

  <div class="alert alert-warning d-flex align-items-start gap-2">
    <FontAwesomeIcon :icon="faTriangleExclamation" class="mt-1" />
    <div class="small">
      Disable or delete any user's API key. All actions are recorded in the
      audit log and attributed to you.
    </div>
  </div>

  <div class="d-flex gap-2 align-items-end mb-3">
    <div>
      <label class="form-label small text-muted mb-1">Filter by user</label>
      <select v-model="userFilter" class="form-select form-select-sm">
        <option value="">all users</option>
        <option v-for="u in users" :key="u.id" :value="u.id">
          {{ u.email }}
        </option>
      </select>
    </div>
    <button class="btn btn-outline-primary btn-sm" @click="applyFilter">
      apply
    </button>
    <button
      v-if="userFilter"
      class="btn btn-outline-secondary btn-sm"
      @click="clearFilter"
    >
      clear
    </button>
  </div>

  <Spinner v-if="adminStatus.loading" />
  <div v-if="adminStatus.error" class="text-danger">
    Error loading API keys: {{ adminStatus.error }}
  </div>

  <div v-if="!adminStatus.loading" class="table-responsive-sm">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th>owner</th>
          <th>status</th>
          <th>scopes</th>
          <th>expires</th>
          <th>last used</th>
          <th>created</th>
          <th class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!adminApiKeys.length">
          <td colspan="8" class="text-center text-muted fst-italic">
            no API keys match the current filter
          </td>
        </tr>
        <tr v-for="k in adminApiKeys" :key="k.id">
          <td>
            <div class="fw-semibold">{{ k.name }}</div>
            <div v-if="k.comment" class="small text-muted">{{ k.comment }}</div>
          </td>
          <td>
            <code>{{ ownerLabel(k) }}</code>
          </td>
          <td>
            <span
              v-if="k.admin_disabled"
              class="badge bg-danger me-1"
              title="Locked by an administrator"
            >
              admin locked
            </span>
            <span
              v-if="k.disabled"
              class="badge bg-warning text-dark me-1"
              title="Disabled by the owner"
            >
              owner disabled
            </span>
            <span
              v-if="!k.admin_disabled && !k.disabled"
              class="badge bg-success"
            >
              active
            </span>
          </td>
          <td style="max-width: 30rem">
            <span
              v-for="scope in k.scopes"
              :key="scope"
              class="badge me-1 mb-1"
              :class="{
                'bg-primary': scope.endsWith(':*') || scope === '*',
                'bg-secondary': !(scope.endsWith(':*') || scope === '*'),
              }"
              >{{ scope }}</span
            >
          </td>
          <td>
            <span v-if="isExpired(k.expires_at)" class="text-danger">
              {{ formatDate(k.expires_at) }} (expired)
            </span>
            <span v-else>{{ formatDate(k.expires_at) }}</span>
          </td>
          <td>{{ formatDate(k.last_used_at) }}</td>
          <td>{{ formatDate(k.created_at) }}</td>
          <td class="text-end">
            <button
              class="btn btn-outline-warning btn-sm me-1"
              @click="toggleDisabled(k)"
              :title="k.admin_disabled ? 'unlock' : 'lock'"
            >
              <FontAwesomeIcon :icon="k.admin_disabled ? faCheck : faBan" />
            </button>
            <button
              class="btn btn-outline-danger btn-sm"
              @click="remove(k)"
              title="delete"
            >
              <FontAwesomeIcon :icon="faTrash" />
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
