<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { router } from "@/router";
import {
  useLocalWarninglistsStore,
  useAuthStore,
  useToastsStore,
} from "@/stores";
import { authHelper } from "@/helpers";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";

// One of your organisation's own warninglists: its entries, import and
// export, and the URL it syncs from.
const props = defineProps({ id: { type: [String, Number], required: true } });

const listsStore = useLocalWarninglistsStore();
const toastsStore = useToastsStore();
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(() =>
  authHelper.hasScope(scopes.value, "local_warninglists:manage"),
);

const KINDS = {
  value: "exact value",
  cidr: "address range",
  suffix: "domain and subdomains",
  regex: "regex",
};
const SIZE = 50;

const list = ref(null);
const page = ref({ total: 0, items: [] });
const currentPage = ref(1);
const query = ref("");
const loading = ref(true);
const error = ref(null);
const selected = ref(new Set());
const settings = ref({});
const newEntry = ref({ value: "", comment: "", expires_at: "" });
const importText = ref("");
const importReplace = ref(false);
const busy = ref(false);

const hasNextPage = computed(
  () => currentPage.value * SIZE < (page.value.total || 0),
);

async function loadEntries() {
  page.value = await listsStore.entries(props.id, {
    q: query.value.trim(),
    page: currentPage.value,
    size: SIZE,
  });
  selected.value = new Set();
}

async function load() {
  loading.value = true;
  error.value = null;
  try {
    list.value = await listsStore.get(props.id);
    settings.value = {
      name: list.value.name,
      description: list.value.description || "",
      source_url: list.value.source_url || "",
      enabled: list.value.enabled,
    };
    await loadEntries();
  } catch (e) {
    error.value = e;
  } finally {
    loading.value = false;
  }
}

async function run(action, done) {
  busy.value = true;
  try {
    const result = await action();
    if (done) toastsStore.push(done(result), "success");
    await load();
  } catch (e) {
    toastsStore.push(`${e}`, "danger");
  } finally {
    busy.value = false;
  }
}

const reflagging = "attributes are being re-checked";

function saveSettings() {
  run(
    () =>
      listsStore.update(props.id, {
        ...settings.value,
        source_url: settings.value.source_url.trim() || null,
      }),
    () => "List saved.",
  );
}

function addEntry() {
  const entry = {
    value: newEntry.value.value.trim(),
    comment: newEntry.value.comment.trim() || null,
    expires_at: newEntry.value.expires_at
      ? new Date(newEntry.value.expires_at).toISOString()
      : null,
  };
  if (!entry.value) return;
  run(
    () => listsStore.addEntries(props.id, [entry]),
    (r) => `${r.added ? "Entry added" : "Entry updated"}; ${reflagging}.`,
  ).then(() => (newEntry.value = { value: "", comment: "", expires_at: "" }));
}

function importEntries() {
  if (!importText.value.trim()) return;
  run(
    () =>
      listsStore.importText(props.id, importText.value, importReplace.value),
    (r) =>
      `${r.added} added, ${r.updated} updated, ${r.removed} removed; ${reflagging}.`,
  ).then(() => (importText.value = ""));
}

function deleteSelected() {
  if (!selected.value.size) return;
  if (
    !confirm(
      `Delete ${selected.value.size} entr${selected.value.size === 1 ? "y" : "ies"}?`,
    )
  )
    return;
  run(
    () => listsStore.deleteEntries(props.id, [...selected.value]),
    (r) => `${r.removed} removed; ${reflagging}.`,
  );
}

function syncNow() {
  run(
    () => listsStore.sync(props.id),
    (l) => (l.sync_error ? `Sync failed: ${l.sync_error}` : "Synced."),
  );
}

async function exportList() {
  try {
    const text = await listsStore.exportText(props.id);
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `warninglist-${props.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toastsStore.push(`${e}`, "danger");
  }
}

async function removeList() {
  if (!confirm(`Delete the list "${list.value.name}" and its entries?`)) return;
  try {
    await listsStore.remove(props.id);
    toastsStore.push(`"${list.value.name}" deleted.`, "success");
    router.push("/settings/warninglists");
  } catch (e) {
    toastsStore.push(`${e}`, "danger");
  }
}

function toggle(entry) {
  const next = new Set(selected.value);
  if (next.has(entry.id)) next.delete(entry.id);
  else next.add(entry.id);
  selected.value = next;
}

const expired = (entry) =>
  entry.expires_at && new Date(entry.expires_at) <= new Date();
const shown = (entry) =>
  entry.kind === "suffix" ? `*.${entry.value}` : entry.value;

load();
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex flex-wrap gap-2 justify-content-between align-items-center"
    >
      <h4 class="mb-0">
        <RouterLink to="/settings/warninglists" class="text-decoration-none"
          >Warninglists</RouterLink
        >
        <span class="text-muted fw-light"> · {{ list?.name }}</span>
      </h4>
      <div v-if="list" class="d-flex gap-2">
        <button
          type="button"
          class="btn btn-outline-secondary btn-sm"
          @click="exportList"
        >
          Export
        </button>
        <button
          v-if="canManage"
          type="button"
          class="btn btn-outline-danger btn-sm"
          @click="removeList"
        >
          Delete list
        </button>
      </div>
    </div>
    <div class="card-body">
      <Spinner v-if="loading && !list" />
      <div v-else-if="error" class="alert alert-danger">{{ error }}</div>
      <template v-else-if="list">
        <p class="text-muted">
          Values never to act on in your environment. They are flagged on
          attributes and indicators, and the detection profiles attaching this
          list leave them out. Only your organisation sees its entries.
        </p>

        <fieldset :disabled="!canManage || busy" class="row g-2 mb-4">
          <div class="col-12 col-md-4">
            <label class="form-label small" for="list-name">Name</label>
            <input
              id="list-name"
              v-model="settings.name"
              class="form-control"
            />
          </div>
          <div class="col-12 col-md-8">
            <label class="form-label small" for="list-description"
              >Description</label
            >
            <input
              id="list-description"
              v-model="settings.description"
              class="form-control"
            />
          </div>
          <div class="col-12 col-md-8">
            <label class="form-label small" for="list-source"
              >Sync daily from (a plain list, one entry per line)</label
            >
            <input
              id="list-source"
              v-model="settings.source_url"
              class="form-control font-monospace"
              placeholder="https://cmdb.corp.example/ranges.txt"
            />
            <div v-if="list.source_url" class="form-text">
              <template v-if="list.synced_at">
                Synced <Timestamp :timestamp="list.synced_at" />.
              </template>
              <span v-if="list.sync_error" class="text-danger">{{
                list.sync_error
              }}</span>
              <button
                type="button"
                class="btn btn-link btn-sm p-0 ms-1"
                @click="syncNow"
              >
                Sync now
              </button>
            </div>
          </div>
          <div class="col-6 col-md-2 d-flex align-items-end">
            <div class="form-check form-switch mb-2">
              <input
                id="list-enabled"
                v-model="settings.enabled"
                class="form-check-input"
                type="checkbox"
              />
              <label class="form-check-label" for="list-enabled">Enabled</label>
            </div>
          </div>
          <div class="col-6 col-md-2 d-flex align-items-end">
            <button
              type="button"
              class="btn btn-primary w-100"
              @click="saveSettings"
            >
              Save
            </button>
          </div>
        </fieldset>

        <div v-if="canManage" class="row g-3 mb-4">
          <div class="col-12 col-lg-6">
            <h6 class="fw-semibold">Add an entry</h6>
            <form class="row g-2" @submit.prevent="addEntry">
              <div class="col-12">
                <input
                  v-model="newEntry.value"
                  class="form-control font-monospace"
                  placeholder="10.0.0.0/8, *.corp.example, vpn.corp.example, /^vpn-\d+\./"
                  aria-label="Entry"
                />
                <div class="form-text">
                  A CIDR is a range, <code>*.domain</code> a domain and its
                  subdomains, <code>/…/</code> a regex; anything else an exact
                  value.
                </div>
              </div>
              <div class="col-12 col-md-6">
                <input
                  v-model="newEntry.comment"
                  class="form-control"
                  placeholder="why, who owns it"
                  aria-label="Comment"
                />
              </div>
              <div class="col-8 col-md-4">
                <input
                  v-model="newEntry.expires_at"
                  class="form-control"
                  type="date"
                  aria-label="Expires"
                  title="Expires (optional)"
                />
              </div>
              <div class="col-4 col-md-2">
                <button
                  class="btn btn-outline-primary w-100"
                  type="submit"
                  :disabled="busy"
                >
                  Add
                </button>
              </div>
            </form>
          </div>
          <div class="col-12 col-lg-6">
            <h6 class="fw-semibold">Import</h6>
            <textarea
              v-model="importText"
              class="form-control font-monospace mb-2"
              rows="3"
              placeholder="One entry per line, entry  # comment"
              aria-label="Entries to import"
            ></textarea>
            <div class="d-flex align-items-center gap-3">
              <div class="form-check mb-0">
                <input
                  id="import-replace"
                  v-model="importReplace"
                  class="form-check-input"
                  type="checkbox"
                />
                <label class="form-check-label small" for="import-replace"
                  >Replace earlier imports</label
                >
              </div>
              <button
                type="button"
                class="btn btn-outline-primary btn-sm ms-auto"
                :disabled="busy || !importText.trim()"
                @click="importEntries"
              >
                Import
              </button>
            </div>
          </div>
        </div>

        <form
          class="d-flex flex-wrap gap-2 align-items-center mb-2"
          @submit.prevent="
            currentPage = 1;
            loadEntries();
          "
        >
          <input
            v-model="query"
            class="form-control form-control-sm font-monospace"
            style="max-width: 320px"
            placeholder="find an entry"
            aria-label="Find an entry"
          />
          <span class="small text-muted"
            >{{ page.total.toLocaleString() }} entries</span
          >
          <button
            v-if="canManage && selected.size"
            type="button"
            class="btn btn-outline-danger btn-sm ms-auto"
            @click="deleteSelected"
          >
            Delete {{ selected.size }}
          </button>
        </form>
        <div class="table-responsive">
          <table class="table table-sm align-middle">
            <thead>
              <tr>
                <th v-if="canManage" style="width: 1%"></th>
                <th>entry</th>
                <th>kind</th>
                <th>comment</th>
                <th>expires</th>
                <th>added</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="entry in page.items"
                :key="entry.id"
                :class="{ 'text-muted': expired(entry) }"
              >
                <td v-if="canManage">
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :aria-label="`Select ${entry.value}`"
                    :checked="selected.has(entry.id)"
                    @change="toggle(entry)"
                  />
                </td>
                <td class="font-monospace text-break">{{ shown(entry) }}</td>
                <td class="small">{{ KINDS[entry.kind] }}</td>
                <td class="small text-break">{{ entry.comment || "—" }}</td>
                <td class="small">
                  <template v-if="entry.expires_at">
                    <Timestamp :timestamp="entry.expires_at" />
                    <span
                      v-if="expired(entry)"
                      class="badge text-bg-light border ms-1"
                      >expired</span
                    >
                  </template>
                  <template v-else>never</template>
                </td>
                <td class="small">
                  <Timestamp :timestamp="entry.created_at" />
                  <span
                    v-if="entry.origin !== 'manual'"
                    class="badge text-bg-light border ms-1"
                    >{{ entry.origin }}</span
                  >
                </td>
              </tr>
              <tr v-if="!page.items.length">
                <td colspan="6" class="text-center text-muted py-4">
                  No entries yet.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Pagination
          :currentPage="currentPage"
          :hasPrevPage="currentPage > 1"
          :hasNextPage="hasNextPage"
          @prevPageClick="
            currentPage--;
            loadEntries();
          "
          @nextPageClick="
            currentPage++;
            loadEntries();
          "
        />
      </template>
    </div>
  </div>
</template>
