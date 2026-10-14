<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useAlertReceiversStore } from "@/stores";

// Creates an alert receiver, or with `receiver` edits its settings. The
// mapping is edited on the receiver's page, next to the test console.
const props = defineProps({
  modalId: { type: String, default: "alertReceiverFormModal" },
  receiver: { type: Object, default: null },
});
const emit = defineEmits(["saved"]);

const receiversStore = useAlertReceiversStore();
const { presets, presetsById } = storeToRefs(receiversStore);

const BLANK = {
  name: "",
  description: "",
  preset: "splunk",
  only_known: true,
  rate_limit: 120,
  allowed_ips: "",
  enabled: true,
};

const modalEl = ref(null);
const form = ref({ ...BLANK });
const saving = ref(false);
const error = ref(null);
const isEdit = computed(() => !!props.receiver);
const presetChanged = computed(
  () => isEdit.value && form.value.preset !== props.receiver.preset,
);

function reset() {
  form.value = props.receiver
    ? {
        ...Object.fromEntries(
          Object.keys(BLANK).map((k) => [k, props.receiver[k]]),
        ),
        allowed_ips: (props.receiver.allowed_ips || []).join(", "),
      }
    : { ...BLANK };
  error.value = null;
}
watch(() => props.receiver, reset, { immediate: true });

onMounted(() => {
  modalEl.value.addEventListener("show.bs.modal", reset);
  receiversStore.getPresets().catch(() => {});
});

async function submit() {
  if (!form.value.name.trim()) {
    error.value = "Name the receiver (the sender posting to it, say).";
    return;
  }
  saving.value = true;
  error.value = null;
  const payload = {
    ...form.value,
    name: form.value.name.trim(),
    description: form.value.description?.trim() || null,
    allowed_ips: form.value.allowed_ips
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean),
  };
  try {
    const saved = isEdit.value
      ? await receiversStore.update(props.receiver.id, payload)
      : await receiversStore.create(payload);
    Modal.getInstance(modalEl.value)?.hide();
    emit("saved", saved);
  } catch (err) {
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
            {{ isEdit ? `Edit "${receiver.name}"` : "New alert webhook" }}
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-md-6">
              <label class="form-label" for="receiver-name">Name</label>
              <input
                id="receiver-name"
                v-model="form.name"
                class="form-control"
                placeholder="Splunk: C2 alerts"
                required
              />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="receiver-preset">Sender</label>
              <select
                id="receiver-preset"
                v-model="form.preset"
                class="form-select"
              >
                <option v-for="p in presets" :key="p.preset" :value="p.preset">
                  {{ p.name }}
                </option>
              </select>
              <div class="form-text">
                <template v-if="presetChanged"
                  >Saving replaces the mapping with this sender's.</template
                >
                <template v-else
                  >Its mapping is where to start; you can change it
                  after.</template
                >
              </div>
            </div>
            <div class="col-12">
              <label class="form-label" for="receiver-description"
                >Description</label
              >
              <input
                id="receiver-description"
                v-model="form.description"
                class="form-control"
                placeholder="Which searches or rules post to it"
              />
            </div>
            <div class="col-md-8">
              <label class="form-label" for="receiver-ips">Only from</label>
              <input
                id="receiver-ips"
                v-model="form.allowed_ips"
                class="form-control font-monospace"
                placeholder="192.0.2.10, 198.51.100.0/24"
              />
              <div class="form-text">
                The sender's addresses. Empty: from anywhere.
              </div>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="receiver-rate"
                >At most (requests a minute)</label
              >
              <input
                id="receiver-rate"
                v-model.number="form.rate_limit"
                type="number"
                min="1"
                max="10000"
                class="form-control"
              />
            </div>
            <div class="col-12">
              <div class="form-check form-switch">
                <input
                  id="receiver-known"
                  v-model="form.only_known"
                  class="form-check-input"
                  type="checkbox"
                />
                <label class="form-check-label" for="receiver-known"
                  >Only values an attribute holds</label
                >
              </div>
              <div class="form-text mt-0 mb-2">
                An alert also names the internal hosts it was raised for; those
                are left out. Off, every value it carries is a sighting.
              </div>
              <div class="form-check form-switch">
                <input
                  id="receiver-enabled"
                  v-model="form.enabled"
                  class="form-check-input"
                  type="checkbox"
                />
                <label class="form-check-label" for="receiver-enabled"
                  >Enabled</label
                >
              </div>
            </div>
          </div>
          <div v-if="error" class="alert alert-danger small mt-3 mb-0">
            {{ error }}
          </div>
          <div
            v-if="!isEdit && presetsById[form.preset]"
            class="small text-muted mt-3"
          >
            {{ presetsById[form.preset].setup }}
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
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? "Saving…" : isEdit ? "Save" : "Create" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
