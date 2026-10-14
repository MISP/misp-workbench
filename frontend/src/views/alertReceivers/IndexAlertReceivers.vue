<script setup>
import { ref, computed, nextTick } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAlertReceiversStore, useAuthStore, useToastsStore } from "@/stores";
import { authHelper } from "@/helpers";
import { router } from "@/router";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import AlertReceiverFormModal from "@/components/alertReceivers/AlertReceiverFormModal.vue";

const receiversStore = useAlertReceiversStore();
const toastsStore = useToastsStore();
const { receivers, presetsById, status } = storeToRefs(receiversStore);
const { scopes } = storeToRefs(useAuthStore());
const canManage = computed(
  () =>
    authHelper.hasScope(scopes.value, "alert_receivers:manage") &&
    authHelper.hasScope(scopes.value, "sightings:create"),
);

receiversStore.getAll();
receiversStore.getPresets().catch(() => {});

function created(receiver) {
  // Its URL is shown once, on its page.
  receiversStore.fresh = {
    id: receiver.id,
    url: receiversStore.urlOf(receiver.path),
  };
  router.push(`/alert-receivers/${receiver.id}`);
}

// The receiver being edited, in the edit dialog.
const editing = ref(null);

async function edit(receiver) {
  editing.value = receiver;
  await nextTick();
  Modal.getOrCreateInstance(
    document.getElementById("alertReceiverEditModal"),
  ).show();
}

function saved(receiver) {
  toastsStore.push(`"${receiver.name}" saved.`, "success");
  receiversStore.getAll();
}

async function remove(receiver) {
  if (
    !confirm(
      `Delete "${receiver.name}"? Its senders get a 404 from now on; the sightings it reported stay.`,
    )
  )
    return;
  try {
    await receiversStore.remove(receiver.id);
    toastsStore.push(`"${receiver.name}" deleted.`, "success");
    receiversStore.getAll();
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
      <h4 class="mb-0">Alert webhooks</h4>
      <button
        v-if="canManage"
        type="button"
        class="btn btn-primary btn-sm"
        data-bs-toggle="modal"
        data-bs-target="#alertReceiverFormModal"
      >
        + New webhook
      </button>
    </div>
    <div class="card-body">
      <p class="text-muted">
        SIEMs and SOARs post their alerts here, in their own shape (Splunk,
        Elastic, Graylog, Wazuh, Sentinel, or any JSON). Each webhook reads the
        values an alert hit out of it and reports them as your organisation's
        sightings, which scoring, hit-rate expiry and false-positive feedback
        learn from.
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
              <th>sender</th>
              <th class="text-end">requests</th>
              <th class="text-end">sightings</th>
              <th>last received</th>
              <th v-if="canManage" class="text-end">actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in receivers" :key="r.id">
              <td>
                <RouterLink :to="`/alert-receivers/${r.id}`">{{
                  r.name
                }}</RouterLink>
                <span v-if="!r.enabled" class="badge text-bg-secondary ms-2"
                  >disabled</span
                >
                <div v-if="r.description" class="small text-muted">
                  {{ r.description }}
                </div>
              </td>
              <td class="small">
                {{ presetsById[r.preset]?.name ?? r.preset }}
              </td>
              <td class="text-end font-monospace">
                {{ r.received_count.toLocaleString() }}
              </td>
              <td class="text-end font-monospace">
                {{ r.sightings_count.toLocaleString() }}
              </td>
              <td class="small">
                <Timestamp
                  v-if="r.last_received_at"
                  :timestamp="r.last_received_at"
                />
                <span v-else class="text-muted">never</span>
                <span
                  v-if="r.last_error"
                  class="badge text-bg-danger ms-1"
                  :title="r.last_error"
                  >refused</span
                >
              </td>
              <td v-if="canManage" class="text-end text-nowrap">
                <button
                  type="button"
                  class="btn btn-outline-primary btn-sm me-1"
                  @click="edit(r)"
                >
                  Edit
                </button>
                <button
                  type="button"
                  class="btn btn-outline-danger btn-sm"
                  @click="remove(r)"
                >
                  Delete
                </button>
              </td>
            </tr>
            <tr v-if="!receivers.length">
              <td
                :colspan="canManage ? 6 : 5"
                class="text-center text-muted py-4"
              >
                No webhook yet.
                <template v-if="canManage"
                  >Create one with "+ New webhook".</template
                >
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <AlertReceiverFormModal v-if="canManage" @saved="created" />
    <AlertReceiverFormModal
      v-if="canManage"
      modal-id="alertReceiverEditModal"
      :receiver="editing"
      @saved="saved"
    />
  </div>
</template>
