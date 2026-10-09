<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useWarninglistsStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";
import Spinner from "@/components/misc/Spinner.vue";

const warninglistsStore = useWarninglistsStore();
const authStore = useAuthStore();
const toastsStore = useToastsStore();
const { warninglists, status } = storeToRefs(warninglistsStore);
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "warninglists:update"),
);

const search = ref("");
const togglingId = ref(null);

// Checking values against the lists, for analysts.
const checkInput = ref("");
const checkResult = ref(null);
const checking = ref(false);

warninglistsStore.getAll();

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase();
  if (!term) return warninglists.value;
  return warninglists.value.filter(
    (w) =>
      w.name.toLowerCase().includes(term) ||
      (w.description || "").toLowerCase().includes(term) ||
      (w.category || "").toLowerCase().includes(term),
  );
});

const enabledCount = computed(
  () => warninglists.value.filter((w) => w.enabled).length,
);

async function toggle(list) {
  togglingId.value = list.id;
  try {
    const updated = await warninglistsStore.setEnabled(list.id, !list.enabled);
    list.enabled = updated.enabled;
    toastsStore.push(
      `"${list.name}" ${list.enabled ? "enabled" : "disabled"}; attributes are being re-checked.`,
      "success",
    );
  } catch (error) {
    toastsStore.push(`Could not update "${list.name}": ${error}`, "danger");
  } finally {
    togglingId.value = null;
  }
}

async function updateLists() {
  try {
    const task = await warninglistsStore.update();
    toastsStore.push(
      `Warninglists update queued (task ${task.task_id}). Attributes are re-checked afterwards.`,
      "success",
    );
  } catch (error) {
    toastsStore.push(`Could not queue the update: ${error}`, "danger");
  }
}

async function check() {
  const values = checkInput.value
    .split(/\s+/)
    .map((v) => v.trim())
    .filter(Boolean);
  if (!values.length) return;
  checking.value = true;
  try {
    const response = await warninglistsStore.check(values);
    checkResult.value = values.map((value) => ({
      value,
      hits: response.hits[value] || [],
    }));
  } catch (error) {
    toastsStore.push(`Check failed: ${error}`, "danger");
  } finally {
    checking.value = false;
  }
}
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Warninglists</h4>
      <button
        v-if="canUpdate"
        class="btn btn-outline-primary btn-sm"
        :disabled="status.updating"
        @click="updateLists"
      >
        {{ status.updating ? "Queuing…" : "Update warninglists" }}
      </button>
    </div>
    <div class="card-body">
      <p class="text-muted">
        Values known to be benign or too common to act on: public resolvers, top
        domains, cloud and CDN ranges, private networks. Attributes on an
        enabled list are flagged, and left out of exports, feeds, sinks and
        lookups by default.
        <span v-if="warninglists.length"
          >{{ enabledCount }} of {{ warninglists.length }} lists enabled.</span
        >
      </p>

      <div class="card bg-body-tertiary border-0 mb-4">
        <div class="card-body py-3">
          <label class="form-label fw-semibold" for="warninglist-check"
            >Check values</label
          >
          <div class="input-group">
            <input
              id="warninglist-check"
              class="form-control font-monospace"
              v-model="checkInput"
              placeholder="8.8.8.8 example.com 10.0.0.1"
              @keyup.enter="check"
            />
            <button
              class="btn btn-outline-secondary"
              :disabled="checking"
              @click="check"
            >
              {{ checking ? "…" : "Check" }}
            </button>
          </div>
          <ul v-if="checkResult" class="list-unstyled small mt-2 mb-0">
            <li v-for="r in checkResult" :key="r.value">
              <code>{{ r.value }}</code>
              <span v-if="r.hits.length" class="text-warning-emphasis">
                — on {{ r.hits.join(", ") }}</span
              >
              <span v-else class="text-muted"> — not on any enabled list</span>
            </li>
          </ul>
        </div>
      </div>

      <input
        class="form-control mb-3"
        v-model="search"
        placeholder="Filter by name, description or category"
      />

      <Spinner v-if="status.loading && !warninglists.length" />
      <div v-else-if="!warninglists.length" class="text-muted">
        No warninglists loaded yet.
        <span v-if="canUpdate">Use "Update warninglists" to load them.</span>
      </div>
      <div v-else class="table-responsive">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>name</th>
              <th v-if="!$isMobile">type</th>
              <th v-if="!$isMobile">applies to</th>
              <th class="text-end">entries</th>
              <th class="text-end">enabled</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="list in filtered" :key="list.id">
              <td>
                <div :class="{ 'text-muted': !list.enabled }">
                  {{ list.name }}
                </div>
                <div
                  v-if="list.description"
                  class="small text-muted text-truncate"
                  style="max-width: 520px"
                  :title="list.description"
                >
                  {{ list.description }}
                </div>
              </td>
              <td v-if="!$isMobile">
                <span class="badge bg-light text-dark">{{ list.type }}</span>
              </td>
              <td
                v-if="!$isMobile"
                class="small text-muted text-truncate"
                style="max-width: 220px"
                :title="list.matching_attributes.join(', ')"
              >
                {{ list.matching_attributes.join(", ") || "all types" }}
              </td>
              <td class="text-end small">
                {{ list.entry_count.toLocaleString() }}
              </td>
              <td class="text-end">
                <div class="form-check form-switch d-inline-block mb-0">
                  <input
                    class="form-check-input"
                    type="checkbox"
                    role="switch"
                    :checked="list.enabled"
                    :disabled="!canUpdate || togglingId === list.id"
                    :aria-label="`${list.enabled ? 'Disable' : 'Enable'} ${list.name}`"
                    @change="toggle(list)"
                  />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
