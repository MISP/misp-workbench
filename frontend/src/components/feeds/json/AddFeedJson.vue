<script setup>
import { ref, reactive, watch, computed } from "vue";
import { useFeedsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSpinner, faChevronDown } from "@fortawesome/free-solid-svg-icons";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";

const attributeProperties = [
  {
    key: "comment",
    label: "comment",
    help: "Free-text comment for the attribute",
  },
  {
    key: "tags",
    label: "tags",
    help: "Comma-separated list of tags",
  },
  {
    key: "to_ids",
    label: "to_ids",
    help: "Whether the attribute should be marked as to_ids (true/false)",
  },
];

const feedsStore = useFeedsStore();
const emit = defineEmits(["update:modelValue"]);

const props = defineProps({
  modelValue: { type: Object, required: true },
});

const apiError = ref(null);
const previewItems = ref([]);
const processedPreview = ref([]);
const loadingPreview = ref(false);

const saved = props.modelValue?.settings?.jsonConfig;

const jsonConfig = reactive({
  format: saved?.format ?? "array",
  items_path: saved?.items_path ?? "",
  attribute: {
    value: saved?.attribute?.value ?? "",
    type: {
      strategy: saved?.attribute?.type?.strategy ?? "fixed",
      value: saved?.attribute?.type?.value ?? null,
      field: saved?.attribute?.type?.field ?? "",
      mappings: saved?.attribute?.type?.mappings ?? [],
    },
    properties: {
      comment: saved?.attribute?.properties?.comment ?? null,
      tags: saved?.attribute?.properties?.tags ?? null,
      to_ids: saved?.attribute?.properties?.to_ids ?? null,
    },
  },
});

watch(
  jsonConfig,
  () => {
    emit("update:modelValue", {
      ...props.modelValue,
      settings: { jsonConfig: { ...jsonConfig } },
    });
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
  () => jsonConfig.format,
  () => {
    if (props.modelValue.url) loadPreview();
  },
);

watch(
  () => [
    jsonConfig.attribute.value,
    jsonConfig.attribute.type.strategy,
    jsonConfig.attribute.type.value,
    jsonConfig.attribute.type.field,
    jsonConfig.attribute.type.mappings,
  ],
  () => {
    if (props.modelValue.url && previewItems.value.length) loadPreview();
  },
  { deep: true },
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

// Initialise properties so v-model bindings work from the start
attributeProperties.forEach((prop) => {
  if (!jsonConfig.attribute.properties[prop.key]) {
    jsonConfig.attribute.properties[prop.key] = {
      strategy: null,
      field: null,
      value: null,
    };
  }
});

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
            @blur="loadPreview"
            @keyup.enter="loadPreview"
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

  <!-- Advanced property mappings -->
  <div class="mb-4">
    <div class="card">
      <div class="card-header py-2">
        <button
          class="btn m-0"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#advancedCardBody"
          aria-expanded="false"
          aria-controls="advancedCardBody"
        >
          Advanced property mappings
          <FontAwesomeIcon :icon="faChevronDown" class="ms-1" />
        </button>
      </div>

      <div class="collapse collapsed" id="advancedCardBody">
        <div class="card-body">
          <div class="text-muted small mb-3">
            Optionally map JSON fields to additional attribute properties.
          </div>

          <div
            v-for="prop in attributeProperties"
            :key="prop.key"
            class="row align-items-center mb-3"
          >
            <!-- LABEL -->
            <label class="col-sm-3 col-form-label">
              {{ prop.label }}
            </label>

            <!-- CONTROLS -->
            <div class="col-sm-9">
              <!-- STRATEGY SWITCH -->
              <div class="d-flex align-items-center gap-3 mb-2">
                <div class="form-check form-check-inline">
                  <input
                    class="form-check-input"
                    type="radio"
                    :name="`prop-${prop.key}`"
                    :value="null"
                    v-model="jsonConfig.attribute.properties[prop.key].strategy"
                  />
                  <label class="form-check-label small text-muted"
                    >Not mapped</label
                  >
                </div>

                <div class="form-check form-check-inline">
                  <input
                    class="form-check-input"
                    type="radio"
                    :name="`prop-${prop.key}`"
                    value="field"
                    v-model="jsonConfig.attribute.properties[prop.key].strategy"
                  />
                  <label class="form-check-label small">Field</label>
                </div>

                <div class="form-check form-check-inline">
                  <input
                    class="form-check-input"
                    type="radio"
                    :name="`prop-${prop.key}`"
                    value="fixed"
                    v-model="jsonConfig.attribute.properties[prop.key].strategy"
                  />
                  <label class="form-check-label small">Fixed value</label>
                </div>
              </div>

              <!-- FIELD SELECT -->
              <div class="col-md-10">
                <div
                  class="row"
                  v-if="
                    jsonConfig.attribute.properties[prop.key].strategy ===
                    'field'
                  "
                >
                  <div class="col-md-6">
                    <input
                      type="text"
                      class="form-control form-control-sm font-monospace"
                      placeholder="Field path (e.g. description)"
                      list="json-field-suggestions"
                      v-model="jsonConfig.attribute.properties[prop.key].field"
                    />
                  </div>
                  <div class="col-md-6">
                    <code>
                      {{
                        previewItems.length > 0 &&
                        jsonConfig.attribute.properties[prop.key].field
                          ? (previewItems[0][
                              jsonConfig.attribute.properties[prop.key].field
                            ] ?? "—")
                          : "—"
                      }}
                    </code>
                  </div>
                </div>

                <!-- FIXED VALUE INPUT -->
                <div class="col-md-6">
                  <div
                    v-if="
                      jsonConfig.attribute.properties[prop.key].strategy ===
                      'fixed'
                    "
                  >
                    <div v-if="prop.key === 'tags'">
                      <TagsSelect
                        :modelClass="'event'"
                        :model="jsonConfig.attribute.properties[prop.key].value"
                        :persist="false"
                        @update:selectedTags="
                          jsonConfig.attribute.properties[prop.key].value =
                            $event
                        "
                      />
                    </div>
                    <div v-else-if="prop.key === 'to_ids'">
                      <select
                        class="form-select form-select-sm"
                        v-model="
                          jsonConfig.attribute.properties[prop.key].value
                        "
                      >
                        <option disabled value="">Select value</option>
                        <option :value="true">true</option>
                        <option :value="false">false</option>
                      </select>
                    </div>
                    <div v-else>
                      <input
                        type="text"
                        class="form-control form-control-sm"
                        v-model="
                          jsonConfig.attribute.properties[prop.key].value
                        "
                        placeholder="Enter fixed value"
                      />
                    </div>
                  </div>
                </div>
              </div>
              <small class="text-muted d-block mt-1">
                {{ prop.help }}
              </small>
            </div>
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
