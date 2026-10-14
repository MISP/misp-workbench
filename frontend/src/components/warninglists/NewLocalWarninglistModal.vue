<script setup>
import { ref, computed, onMounted } from "vue";
import { Modal } from "bootstrap";
import { useLocalWarninglistsStore, useToastsStore } from "@/stores";

// Creates an organisation warninglist: kept by hand, or synced from a URL.
const props = defineProps({
  modalId: { type: String, default: "newLocalWarninglistModal" },
});
const emit = defineEmits(["created"]);

const listsStore = useLocalWarninglistsStore();
const toastsStore = useToastsStore();

const modalEl = ref(null);
const saving = ref(false);
const error = ref(null);
const name = ref("");
const description = ref("");
const kind = ref("manual"); // "manual" | "remote"
const sourceUrl = ref("");
// Hosts lists may sync from (an admin's call); null until loaded.
const sourceHosts = ref(null);

const remoteAllowed = computed(
  () => sourceHosts.value === null || sourceHosts.value.length > 0,
);
const canSubmit = computed(
  () =>
    !saving.value &&
    name.value.trim() &&
    (kind.value === "manual" || sourceUrl.value.trim()),
);

function reset() {
  name.value = "";
  description.value = "";
  kind.value = "manual";
  sourceUrl.value = "";
  error.value = null;
}

onMounted(async () => {
  modalEl.value.addEventListener("hidden.bs.modal", reset);
  sourceHosts.value = await listsStore.sources().catch(() => []);
});

async function submit() {
  if (!canSubmit.value) {
    error.value = name.value.trim()
      ? "A remote list needs a URL."
      : "Name is required.";
    return;
  }
  saving.value = true;
  error.value = null;
  try {
    const created = await listsStore.create({
      name: name.value.trim(),
      description: description.value.trim() || null,
      source_url: kind.value === "remote" ? sourceUrl.value.trim() : null,
    });
    if (created.sync_error) {
      toastsStore.push(
        `"${created.name}" created, but its sync failed: ${created.sync_error}`,
        "warning",
      );
    } else if (created.source_url) {
      toastsStore.push(
        `"${created.name}" created with ${created.entry_count} entries from its URL.`,
        "success",
      );
    } else {
      toastsStore.push(`"${created.name}" created.`, "success");
    }
    Modal.getInstance(modalEl.value)?.hide();
    emit("created", created);
  } catch (err) {
    // Keep the dialog open so a taken name or refused URL can be fixed.
    error.value = `${err}`;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div
    ref="modalEl"
    class="modal fade"
    :id="props.modalId"
    tabindex="-1"
    :aria-labelledby="`${props.modalId}Label`"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <form class="modal-content" @submit.prevent="submit">
        <div class="modal-header">
          <h5 class="modal-title" :id="`${props.modalId}Label`">
            New organisation warninglist
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label" for="nlw-name">Name</label>
            <input
              id="nlw-name"
              v-model="name"
              class="form-control"
              placeholder="Corporate ranges"
              required
            />
            <div class="form-text">Unique within your organisation.</div>
          </div>
          <div class="mb-3">
            <label class="form-label" for="nlw-description">Description</label>
            <textarea
              id="nlw-description"
              v-model="description"
              class="form-control"
              rows="2"
              placeholder="What it holds, who owns it"
            />
          </div>
          <div class="mb-2">
            <span class="form-label d-block">Entries</span>
            <div class="form-check">
              <input
                id="nlw-kind-manual"
                v-model="kind"
                class="form-check-input"
                type="radio"
                value="manual"
              />
              <label class="form-check-label" for="nlw-kind-manual">
                Manual
                <span class="text-muted small d-block">
                  Add entries by hand or import a file on the list's page.
                </span>
              </label>
            </div>
            <div class="form-check mt-2">
              <input
                id="nlw-kind-remote"
                v-model="kind"
                class="form-check-input"
                type="radio"
                value="remote"
                :disabled="!remoteAllowed"
              />
              <label class="form-check-label" for="nlw-kind-remote">
                Remote
                <span class="text-muted small d-block">
                  Synced from a URL now and daily; the URL's content replaces
                  the entries on every sync.
                </span>
              </label>
            </div>
            <div v-if="!remoteAllowed" class="form-text">
              No host is allowed to sync from yet: an admin adds them to
              <code>source_hosts</code> under
              <RouterLink to="/settings/runtime">runtime settings</RouterLink>
              → warninglists.
            </div>
          </div>
          <div v-if="kind === 'remote'" class="mb-3 ms-4">
            <label class="form-label" for="nlw-url">URL</label>
            <input
              id="nlw-url"
              v-model="sourceUrl"
              type="url"
              class="form-control font-monospace"
              placeholder="https://cmdb.corp.example/ranges.txt"
              required
            />
            <div class="form-text">
              A plain list, one entry per line (<code>entry # comment</code>).
              <template v-if="sourceHosts && sourceHosts.length">
                Allowed hosts: <code>{{ sourceHosts.join(", ") }}</code
                >.
              </template>
            </div>
          </div>
          <div v-if="error" class="alert alert-danger small mb-0">
            {{ error }}
          </div>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-outline-secondary"
            data-bs-dismiss="modal"
          >
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" :disabled="!canSubmit">
            {{
              saving
                ? kind === "remote"
                  ? "Creating and syncing…"
                  : "Creating…"
                : "Create"
            }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
