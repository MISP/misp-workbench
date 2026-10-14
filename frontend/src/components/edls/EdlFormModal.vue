<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { useEdlsStore, useDetectionProfilesStore } from "@/stores";

// Creates an external dynamic list, or with `edl` edits it.
const props = defineProps({
  modalId: { type: String, default: "edlFormModal" },
  edl: { type: Object, default: null },
});
const emit = defineEmits(["saved"]);

const edlsStore = useEdlsStore();
const { vendors, vendorsById } = storeToRefs(edlsStore);
const profilesStore = useDetectionProfilesStore();
const { profiles } = storeToRefs(profilesStore);

const LIST_TYPES = {
  ip: "IP addresses and networks",
  domain: "Domains",
  url: "URLs",
  hash: "File hashes",
};
const BLANK = {
  name: "",
  description: "",
  profile_id: null,
  vendor: "paloalto",
  list_type: "ip",
  max_entries: null,
  include_subdomains: false,
  refresh_minutes: 15,
  enabled: true,
};

const modalEl = ref(null);
const form = ref({ ...BLANK });
const saving = ref(false);
const error = ref(null);
const isEdit = computed(() => !!props.edl);

function reset() {
  form.value = props.edl
    ? Object.fromEntries(Object.keys(BLANK).map((k) => [k, props.edl[k]]))
    : { ...BLANK };
  error.value = null;
}
watch(() => props.edl, reset, { immediate: true });

onMounted(() => {
  modalEl.value.addEventListener("show.bs.modal", reset);
  edlsStore.getVendors().catch(() => {});
  if (!profiles.value.length) profilesStore.getAll();
});

const vendor = computed(() => vendorsById.value[form.value.vendor]);
const listTypes = computed(
  () => vendor.value?.list_types ?? Object.keys(LIST_TYPES),
);
// A vendor taking no list of the kind chosen: pick the first it takes.
watch(listTypes, (types) => {
  if (!types.includes(form.value.list_type)) form.value.list_type = types[0];
});
const subdomainsHow = computed(() => {
  if (form.value.list_type !== "domain") return null;
  return {
    paloalto:
      "PAN-OS covers subdomains with its list's own setting: “Automatically expand to include subdomains”.",
    squid: "Written as .example.com, which Squid's dstdomain reads that way.",
    fortinet: "Each domain is followed by *.domain.",
    plain: "Each domain is followed by *.domain.",
  }[form.value.vendor];
});
const canSubdomains = computed(
  () =>
    form.value.list_type === "domain" &&
    ["squid", "fortinet", "plain"].includes(form.value.vendor),
);

async function submit() {
  if (!form.value.name.trim() || !form.value.profile_id) {
    error.value = "A name and a detection profile are required.";
    return;
  }
  saving.value = true;
  error.value = null;
  const payload = {
    ...form.value,
    name: form.value.name.trim(),
    description: form.value.description?.trim() || null,
    max_entries: form.value.max_entries || null,
    include_subdomains: canSubdomains.value && form.value.include_subdomains,
  };
  try {
    const saved = isEdit.value
      ? await edlsStore.update(props.edl.id, payload)
      : await edlsStore.create(payload);
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
            {{ isEdit ? `Edit "${edl.name}"` : "New external dynamic list" }}
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
              <label class="form-label" for="edl-name">Name</label>
              <input
                id="edl-name"
                v-model="form.name"
                class="form-control"
                placeholder="Perimeter block: IPs"
                required
              />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="edl-profile"
                >Detection profile</label
              >
              <select
                id="edl-profile"
                v-model="form.profile_id"
                class="form-select"
                required
              >
                <option :value="null" disabled>Choose one</option>
                <option v-for="p in profiles" :key="p.id" :value="p.id">
                  {{ p.name }}
                </option>
              </select>
              <div class="form-text">What the list holds.</div>
            </div>
            <div class="col-12">
              <label class="form-label" for="edl-description"
                >Description</label
              >
              <input
                id="edl-description"
                v-model="form.description"
                class="form-control"
                placeholder="Which firewalls fetch it"
              />
            </div>
            <div class="col-md-6">
              <label class="form-label" for="edl-vendor">Vendor</label>
              <select id="edl-vendor" v-model="form.vendor" class="form-select">
                <option v-for="v in vendors" :key="v.vendor" :value="v.vendor">
                  {{ v.name }}
                </option>
              </select>
            </div>
            <div class="col-md-6">
              <label class="form-label" for="edl-list-type">Holds</label>
              <select
                id="edl-list-type"
                v-model="form.list_type"
                class="form-select"
              >
                <option v-for="t in listTypes" :key="t" :value="t">
                  {{ LIST_TYPES[t] }}
                </option>
              </select>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="edl-max">At most (entries)</label>
              <input
                id="edl-max"
                v-model.number="form.max_entries"
                type="number"
                min="1"
                class="form-control"
                :placeholder="
                  vendor?.max_entries
                    ? vendor.max_entries.toLocaleString()
                    : 'no limit'
                "
              />
              <div class="form-text">
                The highest scored stay in. Empty: the vendor's limit.
              </div>
            </div>
            <div class="col-md-4">
              <label class="form-label" for="edl-refresh"
                >Rebuilt every (minutes)</label
              >
              <input
                id="edl-refresh"
                v-model.number="form.refresh_minutes"
                type="number"
                min="1"
                class="form-control"
              />
            </div>
            <div class="col-md-4 d-flex flex-column justify-content-center">
              <div class="form-check form-switch">
                <input
                  id="edl-enabled"
                  v-model="form.enabled"
                  class="form-check-input"
                  type="checkbox"
                />
                <label class="form-check-label" for="edl-enabled"
                  >Enabled</label
                >
              </div>
              <div v-if="form.list_type === 'domain'" class="form-check">
                <input
                  id="edl-subdomains"
                  v-model="form.include_subdomains"
                  class="form-check-input"
                  type="checkbox"
                  :disabled="!canSubdomains"
                />
                <label class="form-check-label" for="edl-subdomains"
                  >Subdomains too</label
                >
              </div>
            </div>
            <div v-if="subdomainsHow" class="col-12 form-text mt-0">
              {{ subdomainsHow }}
            </div>
          </div>
          <div v-if="error" class="alert alert-danger small mt-3 mb-0">
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
          <button type="submit" class="btn btn-primary" :disabled="saving">
            {{ saving ? "Saving…" : isEdit ? "Save" : "Create" }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
