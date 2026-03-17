<script setup>
import { ref, reactive, watch } from "vue";
import { useFeedsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";

const feedsStore = useFeedsStore();
const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
  modelValue: {
    type: Object,
    required: true,
  },
});

const apiError = ref(null);
const previewRows = ref([]);
const loadingPreview = ref(false);

const saved = props.modelValue?.settings?.freetextConfig;

const freetextConfig = reactive({
  type_detection: saved?.type_detection ?? "automatic",
  fixed_type: saved?.fixed_type ?? null,
});

// Emit config changes to parent without triggering preview reload
watch(
  freetextConfig,
  () => {
    emit("update:modelValue", {
      ...props.modelValue,
      settings: { freetextConfig: { ...freetextConfig } },
    });
  },
  { deep: true },
);

// Reload preview when URL changes
watch(
  () => props.modelValue.url,
  (newUri, oldUri) => {
    if (newUri && newUri !== oldUri) {
      loadPreview();
    }
  },
  { immediate: true },
);

// Reload preview when switching between automatic/fixed
watch(
  () => freetextConfig.type_detection,
  () => {
    if (props.modelValue.url) loadPreview();
  },
);

// Called only when a valid type is selected from the datalist
function onFixedTypeSelected(type) {
  freetextConfig.fixed_type = type;
  if (props.modelValue.url) loadPreview();
}

function loadPreview() {
  loadingPreview.value = true;
  apiError.value = null;
  feedsStore
    .previewFreetextFeed({
      ...props.modelValue,
      settings: { freetextConfig: { ...freetextConfig } },
    })
    .then((response) => {
      previewRows.value = response?.rows ?? [];
    })
    .catch((error) => (apiError.value = error?.message || String(error)))
    .finally(() => (loadingPreview.value = false));
}

const TYPE_BADGE = {
  "ip-src": "bg-danger",
  "ip-dst": "bg-danger",
  url: "bg-primary",
  domain: "bg-info text-dark",
  "email-src": "bg-warning text-dark",
  md5: "bg-secondary",
  sha1: "bg-secondary",
  sha256: "bg-secondary",
  sha512: "bg-secondary",
  cve: "bg-dark",
};

function typeBadgeClass(type) {
  return TYPE_BADGE[type] ?? "bg-secondary";
}
</script>

<template>
  <div class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">Freetext Settings</h5>
      </div>
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label fw-semibold">Attribute type detection</label>
          <div class="d-flex gap-3">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="typeAutomatic"
                value="automatic"
                v-model="freetextConfig.type_detection"
              />
              <label class="form-check-label" for="typeAutomatic">
                Automatic
                <span class="text-muted small">(heuristics per line)</span>
              </label>
            </div>
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="typeFixed"
                value="fixed"
                v-model="freetextConfig.type_detection"
              />
              <label class="form-check-label" for="typeFixed">Fixed type</label>
            </div>
          </div>
        </div>

        <div v-if="freetextConfig.type_detection === 'fixed'" class="mb-3">
          <label class="form-label" for="fixedType">Attribute type</label>
          <AttributeTypeSelect
            name="fixedType"
            :selected="freetextConfig.fixed_type"
            @attribute-type-updated="onFixedTypeSelected"
          />
        </div>

        <hr class="my-3" />

        <h6 class="text-muted mb-2">Preview</h6>

        <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

        <div v-if="loadingPreview" class="alert alert-info">
          Loading preview… <FontAwesomeIcon :icon="faSpinner" spin />
        </div>

        <div v-else-if="!previewRows.length" class="alert alert-warning mb-0">
          No preview available. Check the URL and source type.
        </div>

        <table v-else class="table table-sm table-bordered mb-0">
          <thead class="table-secondary">
            <tr>
              <th style="width: 30px">#</th>
              <th>Value</th>
              <th style="width: 140px">Type</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in previewRows" :key="idx">
              <td>{{ idx + 1 }}</td>
              <td>
                <code class="small">{{ row.value }}</code>
              </td>
              <td>
                <span class="badge" :class="typeBadgeClass(row.type)">
                  {{ row.type }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>

        <small v-if="previewRows.length" class="text-muted">
          showing first {{ previewRows.length }} row{{
            previewRows.length !== 1 ? "s" : ""
          }}
        </small>
      </div>
    </div>
  </div>
</template>
