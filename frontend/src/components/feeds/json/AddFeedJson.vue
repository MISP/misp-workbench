<script setup>
import { ref, reactive, watch, computed } from "vue";
import { useFeedsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";

const feedsStore = useFeedsStore();
const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
  modelValue: { type: Object, required: true },
});

const apiError = ref(null);
const previewItems = ref([]);
const processedPreview = ref([]);
const loadingPreview = ref(false);

const jsonConfig = reactive({
  format: "array",
  items_path: "",
  attribute: {
    value: "",
    type: {
      strategy: "fixed",
      value: null,
      field: "",
      mappings: [],
    },
    properties: {
      comment: null,
      tags: null,
      to_ids: null,
    },
  },
});

watch(
  jsonConfig,
  () => {
    emit("update:modelValue", { settings: { jsonConfig: { ...jsonConfig } } });
  },
  { deep: true },
);

watch(
  () => props.modelValue.url,
  (newUri, oldUri) => {
    if (newUri && newUri !== oldUri) loadPreview();
  },
  { immediate: true },
);

watch(
  () => jsonConfig.items_path,
  () => {
    if (props.modelValue.url) loadPreview();
  },
);

watch(
  () => jsonConfig.format,
  () => {
    if (props.modelValue.url) loadPreview();
  },
);

function loadPreview() {
  loadingPreview.value = true;
  apiError.value = null;
  feedsStore
    .previewJsonFeed({
      ...props.modelValue,
      settings: { jsonConfig: { ...jsonConfig } },
    })
    .then((response) => {
      previewItems.value = response?.items ?? [];
      processedPreview.value = response?.preview ?? [];
    })
    .catch((error) => (apiError.value = error?.message || String(error)))
    .finally(() => (loadingPreview.value = false));
}

// Keys detected from the first preview item for field suggestions
const sampleKeys = computed(() => {
  const first = previewItems.value[0];
  if (!first || typeof first !== "object") return [];
  return Object.keys(first);
});

function onFixedTypeSelected(type) {
  jsonConfig.attribute.type.value = type;
}

function addTypeMapping() {
  jsonConfig.attribute.type.mappings.push({ from: "", to: "" });
}

function removeTypeMapping(idx) {
  jsonConfig.attribute.type.mappings.splice(idx, 1);
}

function setPropertyStrategy(prop, strategy) {
  if (strategy === "none") {
    jsonConfig.attribute.properties[prop] = null;
  } else if (strategy === "fixed") {
    jsonConfig.attribute.properties[prop] = {
      strategy: "fixed",
      value: prop === "to_ids" ? false : prop === "tags" ? [] : "",
    };
  } else {
    jsonConfig.attribute.properties[prop] = { strategy: "field", field: "" };
  }
}

function getPropertyStrategy(prop) {
  return jsonConfig.attribute.properties[prop]?.strategy ?? "none";
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
};
function typeBadgeClass(type) {
  return TYPE_BADGE[type] ?? "bg-secondary";
}
</script>

<template>
  <!-- JSON Structure Preview -->
  <div class="mb-4">
    <div class="card">
      <div
        class="card-header d-flex justify-content-between align-items-center"
      >
        <h5 class="mb-0">JSON Preview</h5>
        <button
          class="btn btn-outline-secondary btn-sm"
          :disabled="!modelValue.url || loadingPreview"
          @click="loadPreview"
        >
          <FontAwesomeIcon
            v-if="loadingPreview"
            :icon="faSpinner"
            spin
            class="me-1"
          />
          Reload Preview
        </button>
      </div>
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label fw-semibold">Format</label>
          <div class="d-flex gap-3">
            <div
              class="form-check"
              v-for="opt in [
                { value: 'array', label: 'JSON array' },
                { value: 'object', label: 'JSON object' },
                { value: 'ndjson', label: 'NDJSON (one object per line)' },
              ]"
              :key="opt.value"
            >
              <input
                class="form-check-input"
                type="radio"
                :id="`fmt-${opt.value}`"
                :value="opt.value"
                v-model="jsonConfig.format"
              />
              <label class="form-check-label" :for="`fmt-${opt.value}`">{{
                opt.label
              }}</label>
            </div>
          </div>
        </div>

        <div v-if="jsonConfig.format !== 'ndjson'" class="mb-3">
          <label class="form-label fw-semibold">Items path</label>
          <input
            type="text"
            class="form-control font-monospace"
            placeholder="e.g. data.indicators (leave empty if root is the array/object)"
            v-model="jsonConfig.items_path"
          />
          <div class="form-text">
            Dot-notation path to the JSON array or object to ingest. Leave empty
            to use the root.
          </div>
        </div>

        <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

        <div v-if="loadingPreview" class="alert alert-info">
          Loading preview… <FontAwesomeIcon :icon="faSpinner" spin />
        </div>

        <div v-else-if="!previewItems.length" class="alert alert-warning mb-0">
          No preview available. Enter a URL and check the items path.
        </div>

        <div v-else>
          <p class="text-muted small mb-2">
            First {{ previewItems.length }} item{{
              previewItems.length !== 1 ? "s" : ""
            }}
            — detected fields:
            <code>{{ sampleKeys.join(", ") }}</code>
          </p>
          <div
            class="border rounded p-2 bg-body-secondary"
            style="max-height: 240px; overflow-y: auto"
          >
            <pre
              v-for="(item, idx) in previewItems"
              :key="idx"
              class="mb-1 small font-monospace"
              style="white-space: pre-wrap"
              >{{ JSON.stringify(item, null, 2) }}</pre
            >
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Attribute Mapping -->
  <div class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">Attribute Mapping</h5>
      </div>
      <div class="card-body">
        <!-- Value field -->
        <div class="mb-3">
          <label class="form-label fw-semibold"
            >Value field <span class="text-danger">*</span></label
          >
          <input
            type="text"
            class="form-control font-monospace"
            placeholder="e.g. value or nested.field — leave empty to use item directly"
            list="json-field-suggestions"
            v-model="jsonConfig.attribute.value"
          />
          <datalist id="json-field-suggestions">
            <option v-for="key in sampleKeys" :key="key" :value="key" />
          </datalist>
          <div class="form-text">
            <span v-if="previewItems.length && !sampleKeys.length">
              Items are plain values — leave empty to use each item directly.
            </span>
            <span v-else-if="previewItems[0] && jsonConfig.attribute.value">
              Sample:
              <code>{{
                previewItems[0][jsonConfig.attribute.value] ?? "—"
              }}</code>
            </span>
            <span v-else>
              Dot-notation path to the attribute value within each item.
            </span>
          </div>
        </div>

        <!-- Type strategy -->
        <div class="mb-3">
          <label class="form-label fw-semibold">Attribute type</label>
          <div class="d-flex gap-3 mb-2">
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="typeFixed"
                value="fixed"
                v-model="jsonConfig.attribute.type.strategy"
              />
              <label class="form-check-label" for="typeFixed">Fixed type</label>
            </div>
            <div class="form-check">
              <input
                class="form-check-input"
                type="radio"
                id="typeField"
                value="field"
                v-model="jsonConfig.attribute.type.strategy"
              />
              <label class="form-check-label" for="typeField">From field</label>
            </div>
          </div>

          <div v-if="jsonConfig.attribute.type.strategy === 'fixed'">
            <AttributeTypeSelect
              name="fixedType"
              :selected="jsonConfig.attribute.type.value"
              @attribute-type-updated="onFixedTypeSelected"
            />
          </div>

          <div v-else>
            <input
              type="text"
              class="form-control font-monospace mb-2"
              placeholder="Field name (e.g. type)"
              list="json-field-suggestions"
              v-model="jsonConfig.attribute.type.field"
            />
            <div
              v-if="previewItems[0] && jsonConfig.attribute.type.field"
              class="form-text mb-2"
            >
              Sample:
              <code>{{
                previewItems[0][jsonConfig.attribute.type.field] ?? "—"
              }}</code>
            </div>

            <!-- Type mappings -->
            <div class="mt-2">
              <label class="form-label small fw-semibold"
                >Type mappings <span class="text-muted">(optional)</span></label
              >
              <table
                v-if="jsonConfig.attribute.type.mappings.length"
                class="table table-sm table-bordered mb-2"
              >
                <thead class="table-secondary">
                  <tr>
                    <th>Feed value</th>
                    <th>MISP type</th>
                    <th style="width: 40px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(mapping, idx) in jsonConfig.attribute.type.mappings"
                    :key="idx"
                  >
                    <td>
                      <input
                        type="text"
                        class="form-control form-control-sm font-monospace"
                        v-model="mapping.from"
                      />
                    </td>
                    <td>
                      <AttributeTypeSelect
                        :name="`mapping-type-${idx}`"
                        :selected="mapping.to"
                        @attribute-type-updated="(t) => (mapping.to = t)"
                      />
                    </td>
                    <td>
                      <button
                        class="btn btn-sm btn-outline-danger"
                        @click="removeTypeMapping(idx)"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
              <button
                class="btn btn-sm btn-outline-secondary"
                @click="addTypeMapping"
              >
                + Add mapping
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Optional Properties -->
  <div class="mb-4">
    <div class="card">
      <div
        class="card-header d-flex justify-content-between align-items-center"
        style="cursor: pointer"
        data-bs-toggle="collapse"
        data-bs-target="#optionalPropertiesBody"
      >
        <h5 class="mb-0">Optional Properties</h5>
        <i class="bi bi-chevron-down"></i>
      </div>
      <div id="optionalPropertiesBody" class="collapse">
        <div class="card-body">
          <!-- Comment -->
          <div class="mb-3">
            <label class="form-label fw-semibold">Comment</label>
            <div class="d-flex gap-3 mb-2">
              <div
                class="form-check"
                v-for="opt in ['none', 'fixed', 'field']"
                :key="opt"
              >
                <input
                  class="form-check-input"
                  type="radio"
                  :id="`comment-${opt}`"
                  :value="opt"
                  :checked="getPropertyStrategy('comment') === opt"
                  @change="setPropertyStrategy('comment', opt)"
                />
                <label
                  class="form-check-label text-capitalize"
                  :for="`comment-${opt}`"
                  >{{ opt }}</label
                >
              </div>
            </div>
            <input
              v-if="getPropertyStrategy('comment') === 'fixed'"
              type="text"
              class="form-control"
              placeholder="Fixed comment value"
              v-model="jsonConfig.attribute.properties.comment.value"
            />
            <input
              v-if="getPropertyStrategy('comment') === 'field'"
              type="text"
              class="form-control font-monospace"
              placeholder="Field name (e.g. description)"
              list="json-field-suggestions"
              v-model="jsonConfig.attribute.properties.comment.field"
            />
          </div>

          <!-- Tags -->
          <div class="mb-3">
            <label class="form-label fw-semibold">Tags</label>
            <div class="d-flex gap-3 mb-2">
              <div
                class="form-check"
                v-for="opt in ['none', 'fixed', 'field']"
                :key="opt"
              >
                <input
                  class="form-check-input"
                  type="radio"
                  :id="`tags-${opt}`"
                  :value="opt"
                  :checked="getPropertyStrategy('tags') === opt"
                  @change="setPropertyStrategy('tags', opt)"
                />
                <label
                  class="form-check-label text-capitalize"
                  :for="`tags-${opt}`"
                  >{{ opt }}</label
                >
              </div>
            </div>
            <input
              v-if="getPropertyStrategy('tags') === 'fixed'"
              type="text"
              class="form-control"
              placeholder="Comma-separated tags"
              :value="
                (jsonConfig.attribute.properties.tags?.value ?? []).join(', ')
              "
              @input="
                jsonConfig.attribute.properties.tags.value = $event.target.value
                  .split(',')
                  .map((t) => t.trim())
                  .filter(Boolean)
              "
            />
            <input
              v-if="getPropertyStrategy('tags') === 'field'"
              type="text"
              class="form-control font-monospace"
              placeholder="Field name (e.g. tags)"
              list="json-field-suggestions"
              v-model="jsonConfig.attribute.properties.tags.field"
            />
          </div>

          <!-- To IDS -->
          <div class="mb-3">
            <label class="form-label fw-semibold">To IDS</label>
            <div class="d-flex gap-3 mb-2">
              <div
                class="form-check"
                v-for="opt in ['none', 'fixed', 'field']"
                :key="opt"
              >
                <input
                  class="form-check-input"
                  type="radio"
                  :id="`to-ids-${opt}`"
                  :value="opt"
                  :checked="getPropertyStrategy('to_ids') === opt"
                  @change="setPropertyStrategy('to_ids', opt)"
                />
                <label
                  class="form-check-label text-capitalize"
                  :for="`to-ids-${opt}`"
                  >{{ opt }}</label
                >
              </div>
            </div>
            <div
              v-if="getPropertyStrategy('to_ids') === 'fixed'"
              class="form-check form-switch"
            >
              <input
                class="form-check-input"
                type="checkbox"
                id="toIdsFixed"
                v-model="jsonConfig.attribute.properties.to_ids.value"
              />
              <label class="form-check-label" for="toIdsFixed">Enabled</label>
            </div>
            <input
              v-if="getPropertyStrategy('to_ids') === 'field'"
              type="text"
              class="form-control font-monospace"
              placeholder="Field name (e.g. to_ids)"
              list="json-field-suggestions"
              v-model="jsonConfig.attribute.properties.to_ids.field"
            />
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Processed Preview -->
  <div v-if="processedPreview.length" class="mb-4">
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">Attribute Preview</h5>
      </div>
      <div class="card-body">
        <table class="table table-sm table-bordered mb-0">
          <thead class="table-secondary">
            <tr>
              <th style="width: 30px">#</th>
              <th>Value</th>
              <th style="width: 140px">Type</th>
              <th v-if="processedPreview.some((r) => r.comment)">Comment</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in processedPreview"
              :key="idx"
              :class="row.error ? 'table-danger' : ''"
            >
              <td>{{ idx + 1 }}</td>
              <td>
                <code class="small">{{ row.value ?? "—" }}</code>
                <span v-if="row.error" class="text-danger small ms-2">{{
                  row.error
                }}</span>
              </td>
              <td>
                <span
                  v-if="row.type"
                  class="badge"
                  :class="typeBadgeClass(row.type)"
                  >{{ row.type }}</span
                >
                <span v-else class="text-muted small">—</span>
              </td>
              <td v-if="processedPreview.some((r) => r.comment)">
                {{ row.comment ?? "" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
