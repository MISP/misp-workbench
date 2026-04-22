<script setup>
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { useApiKeysStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faPlus,
  faCopy,
  faTriangleExclamation,
  faBan,
  faCheck,
} from "@fortawesome/free-solid-svg-icons";

const apiKeysStore = useApiKeysStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();

const { apiKeys, status } = storeToRefs(apiKeysStore);

const SELECTABLE_SCOPES = ["events:read", "attributes:read", "objects:read"];

const showCreate = ref(false);
const form = ref(newForm());
const formError = ref(null);
const newlyCreated = ref(null);

onMounted(() => {
  apiKeysStore.getAll();
});

function newForm() {
  return {
    name: "",
    comment: "",
    scopes: [],
    expires_at: "",
  };
}

const userScopes = computed(() => authStore.scopes || []);

function scopeAllowed(scope) {
  const scopes = userScopes.value;
  if (scopes.includes("*")) return true;
  const resource = scope.split(":")[0];
  if (scopes.includes(`${resource}:*`)) return true;
  return scopes.includes(scope);
}

const allowedScopes = computed(() =>
  SELECTABLE_SCOPES.filter((s) => scopeAllowed(s)),
);

function toggleScope(scope) {
  const idx = form.value.scopes.indexOf(scope);
  if (idx !== -1) form.value.scopes.splice(idx, 1);
  else form.value.scopes.push(scope);
}

function openCreate() {
  form.value = newForm();
  formError.value = null;
  showCreate.value = true;
}

function closeCreate() {
  showCreate.value = false;
}

async function submitCreate() {
  formError.value = null;
  if (!form.value.name.trim()) {
    formError.value = "Name is required.";
    return;
  }
  if (form.value.scopes.length === 0) {
    formError.value = "Select at least one scope.";
    return;
  }
  const payload = {
    name: form.value.name.trim(),
    comment: form.value.comment.trim() || null,
    scopes: form.value.scopes,
    expires_at: form.value.expires_at
      ? new Date(form.value.expires_at).toISOString()
      : null,
  };
  try {
    const created = await apiKeysStore.create(payload);
    newlyCreated.value = created;
    showCreate.value = false;
    await apiKeysStore.getAll();
  } catch (err) {
    formError.value = err?.message || String(err);
  }
}

async function copyToken() {
  if (!newlyCreated.value) return;
  try {
    await navigator.clipboard.writeText(newlyCreated.value.token);
    toastsStore.push("Token copied to clipboard.", "success");
  } catch {
    toastsStore.push("Could not copy token.", "error");
  }
}

function dismissNewlyCreated() {
  newlyCreated.value = null;
}

async function remove(key) {
  if (!confirm(`Delete API key "${key.name}"? This cannot be undone.`)) return;
  try {
    await apiKeysStore.delete(key.id);
    toastsStore.push("API key deleted.", "success");
    await apiKeysStore.getAll();
  } catch (err) {
    toastsStore.push(`Delete failed: ${err?.message || err}`, "error");
  }
}

const canUpdateApiKeys = computed(() => scopeAllowed("api_keys:update"));

async function toggleDisabled(key) {
  const next = !key.disabled;
  const verb = next ? "Disable" : "Enable";
  if (
    !confirm(
      next
        ? `Disable API key "${key.name}"? It will stop authenticating until re-enabled.`
        : `Re-enable API key "${key.name}"?`,
    )
  )
    return;
  try {
    await apiKeysStore.setDisabled(key.id, next);
    toastsStore.push(`API key ${next ? "disabled" : "enabled"}.`, "success");
  } catch (err) {
    toastsStore.push(`${verb} failed: ${err?.message || err}`, "error");
  }
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
    <h4 class="mb-0">API keys</h4>
    <button class="btn btn-primary btn-sm" @click="openCreate">
      <FontAwesomeIcon :icon="faPlus" /> New API key
    </button>
  </div>

  <p class="text-muted small">
    API keys let third-party tools authenticate against the misp-workbench API.
    Send them as the <code>Authorization</code> header value (MISP-compatible,
    no <code>Bearer</code> prefix required).
  </p>

  <div v-if="newlyCreated" class="alert alert-warning d-flex flex-column gap-2">
    <div>
      <FontAwesomeIcon :icon="faTriangleExclamation" />
      <strong class="ms-2">
        Copy this token now. It will not be shown again.
      </strong>
    </div>
    <div class="d-flex gap-2 align-items-center">
      <code class="flex-grow-1 p-2 bg-white border rounded text-break">
        {{ newlyCreated.token }}
      </code>
      <button class="btn btn-outline-primary btn-sm" @click="copyToken">
        <FontAwesomeIcon :icon="faCopy" /> copy
      </button>
      <button
        class="btn btn-outline-secondary btn-sm"
        @click="dismissNewlyCreated"
      >
        dismiss
      </button>
    </div>
  </div>

  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading API keys: {{ status.error }}
  </div>

  <div v-if="!status.loading" class="table-responsive-sm">
    <table class="table table-striped align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th>status</th>
          <th>scopes</th>
          <th>expires</th>
          <th>last used</th>
          <th>created</th>
          <th class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!apiKeys.length">
          <td colspan="7" class="text-center text-muted fst-italic">
            no API keys yet
          </td>
        </tr>
        <tr v-for="k in apiKeys" :key="k.id">
          <td>
            <div class="fw-semibold">{{ k.name }}</div>
            <div v-if="k.comment" class="small text-muted">{{ k.comment }}</div>
          </td>
          <td>
            <span v-if="k.disabled" class="badge bg-warning text-dark">
              disabled
            </span>
            <span v-else class="badge bg-success">active</span>
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
              v-if="canUpdateApiKeys"
              class="btn btn-outline-warning btn-sm me-1"
              @click="toggleDisabled(k)"
              :title="k.disabled ? 'enable' : 'disable'"
            >
              <FontAwesomeIcon :icon="k.disabled ? faCheck : faBan" />
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

  <div
    v-if="showCreate"
    class="modal d-block"
    tabindex="-1"
    style="background: rgba(0, 0, 0, 0.4)"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">New API key</h5>
          <button type="button" class="btn-close" @click="closeCreate"></button>
        </div>
        <div class="modal-body">
          <div v-if="formError" class="alert alert-danger">{{ formError }}</div>

          <div class="mb-3">
            <label class="form-label">Name</label>
            <input
              v-model="form.name"
              type="text"
              class="form-control"
              placeholder="e.g. Splunk integration"
              maxlength="255"
            />
          </div>

          <div class="mb-3">
            <label class="form-label">Comment (optional)</label>
            <textarea
              v-model="form.comment"
              class="form-control"
              rows="2"
            ></textarea>
          </div>

          <div class="mb-3">
            <label class="form-label">Expires at (optional)</label>
            <input
              v-model="form.expires_at"
              type="datetime-local"
              class="form-control"
            />
          </div>

          <div class="mb-3">
            <label class="form-label">Scopes</label>
            <div class="small text-muted mb-2">
              Only scopes your role allows are selectable.
            </div>
            <div v-if="!allowedScopes.length" class="small text-danger">
              Your role does not permit any of the API-key scopes.
            </div>
            <div v-else>
              <label
                v-for="scope in allowedScopes"
                :key="scope"
                class="form-check"
              >
                <input
                  type="checkbox"
                  class="form-check-input"
                  :checked="form.scopes.includes(scope)"
                  @change="toggleScope(scope)"
                />
                <span class="form-check-label">
                  <code>{{ scope }}</code>
                </span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-outline-secondary"
            @click="closeCreate"
          >
            Cancel
          </button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="status.creating"
            @click="submitCreate"
          >
            <span v-if="status.creating">creating…</span>
            <span v-else>Create</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
