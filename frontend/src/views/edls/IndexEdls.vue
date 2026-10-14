<script setup>
import { ref, computed, nextTick } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useEdlsStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";
import { router } from "@/router";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import EdlFormModal from "@/components/edls/EdlFormModal.vue";

const edlsStore = useEdlsStore();
const toastsStore = useToastsStore();
const { edls, vendorsById, status } = storeToRefs(edlsStore);
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(() =>
  authHelper.hasScope(scopes.value, "edls:manage"),
);

edlsStore.getAll();
edlsStore.getVendors().catch(() => {});

function created(edl) {
  toastsStore.push(
    `"${edl.name}" created. Add a token to get the URL a firewall fetches.`,
    "success",
  );
  router.push(`/edls/${edl.id}`);
}

// The list being edited, in the edit dialog.
const editing = ref(null);

async function edit(edl) {
  editing.value = edl;
  await nextTick();
  Modal.getOrCreateInstance(document.getElementById("edlEditModal")).show();
}

function saved(edl) {
  toastsStore.push(`"${edl.name}" saved; it is being rebuilt.`, "success");
  edlsStore.getAll();
}

// The lists being rebuilt, by id.
const building = ref(new Set());

async function rebuild(edl) {
  building.value = new Set(building.value).add(edl.id);
  try {
    const built = await edlsStore.build(edl.id);
    edls.value = edls.value.map((e) => (e.id === built.id ? built : e));
    if (built.build_error) {
      toastsStore.push(
        `"${built.name}" failed to build: ${built.build_error}`,
        "danger",
      );
    } else {
      toastsStore.push(
        `"${built.name}" rebuilt: ${built.entry_count.toLocaleString()} entries.`,
        "success",
      );
    }
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  } finally {
    const rest = new Set(building.value);
    rest.delete(edl.id);
    building.value = rest;
  }
}

async function remove(edl) {
  if (
    !confirm(
      `Delete "${edl.name}"? Firewalls fetching it get a 404 from now on.`,
    )
  )
    return;
  try {
    await edlsStore.remove(edl.id);
    toastsStore.push(`"${edl.name}" deleted.`, "success");
    edlsStore.getAll();
  } catch (err) {
    toastsStore.push(`${err}`, "danger");
  }
}
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">External dynamic lists</h4>
      <button
        v-if="canManage"
        type="button"
        class="btn btn-primary btn-sm"
        data-bs-toggle="modal"
        data-bs-target="#edlFormModal"
      >
        + New EDL
      </button>
    </div>
    <div class="card-body">
      <p class="text-muted">
        Plain-text lists firewalls and proxies fetch on a schedule (Palo Alto,
        Fortinet, Check Point, Cisco, Squid): a detection profile's IPs,
        domains, URLs or hashes, in the vendor's format. Each is served at a URL
        carrying a token for that list alone.
      </p>
      <Spinner v-if="status.loading" />
      <div v-else-if="status.error" class="alert alert-danger">
        {{ status.error }}
      </div>
      <div v-else class="table-responsive">
        <table class="table align-middle">
          <thead>
            <tr>
              <th>name</th>
              <th>vendor</th>
              <th>holds</th>
              <th class="text-end">entries</th>
              <th>built</th>
              <th class="text-end">tokens</th>
              <th v-if="canManage" class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in edls" :key="e.id">
              <td>
                <RouterLink :to="`/edls/${e.id}`">{{ e.name }}</RouterLink>
                <span v-if="!e.enabled" class="badge text-bg-secondary ms-2"
                  >disabled</span
                >
                <div v-if="e.description" class="small text-muted">
                  {{ e.description }}
                </div>
              </td>
              <td class="small">
                {{ vendorsById[e.vendor]?.name ?? e.vendor }}
              </td>
              <td>{{ e.list_type }}</td>
              <td class="text-end font-monospace">
                {{ e.entry_count?.toLocaleString() ?? "–" }}
                <span
                  v-if="e.truncated"
                  class="badge text-bg-warning ms-1"
                  :title="`${e.truncated.toLocaleString()} lower scored entries left out by the size limit`"
                  >capped</span
                >
              </td>
              <td class="small">
                <span
                  v-if="e.build_error"
                  class="text-danger"
                  :title="e.build_error"
                  >failed</span
                >
                <Timestamp v-else-if="e.built_at" :timestamp="e.built_at" />
                <span v-else class="text-muted">soon</span>
              </td>
              <td class="text-end">{{ e.active_tokens }}</td>
              <td v-if="canManage" class="text-end text-nowrap">
                <button
                  type="button"
                  class="btn btn-outline-secondary btn-sm me-1"
                  :disabled="building.has(e.id)"
                  title="Build it now, rather than at its next refresh"
                  @click="rebuild(e)"
                >
                  {{ building.has(e.id) ? "Rebuilding…" : "Rebuild" }}
                </button>
                <button
                  type="button"
                  class="btn btn-outline-primary btn-sm me-1"
                  @click="edit(e)"
                >
                  Edit
                </button>
                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  @click="remove(e)"
                >
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="!edls.length">
              <td
                :colspan="canManage ? 7 : 6"
                class="text-center text-muted py-4"
              >
                No list yet.
                <template v-if="canManage"
                  >Create one with "+ New EDL".</template
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <EdlFormModal v-if="canManage" @saved="created" />
    <EdlFormModal
      v-if="canManage"
      modal-id="edlEditModal"
      :edl="editing"
      @saved="saved"
    />
  </div>
</template>
