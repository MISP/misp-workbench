<script setup>
import { ref, reactive, onMounted } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useRuntimeSettingsStore, useToastsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faSync,
  faCode,
  faSlidersH,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";
import AttributeTypeSelect from "@/components/enums/AttributeTypeSelect.vue";

const toastsStore = useToastsStore();
const runtimeSettingsStore = useRuntimeSettingsStore();
const { runtimeSettings, status } = storeToRefs(runtimeSettingsStore);

const errors = ref({});
const editableSettings = reactive({});
const jsonMode = reactive({});
const formValues = reactive({});

onMounted(() => {
  runtimeSettingsStore.getAll().then(() => {
    Object.entries(runtimeSettings.value).forEach(([namespace, value]) => {
      editableSettings[namespace] = JSON.stringify(value || {}, null, 4);
      formValues[namespace] = JSON.parse(JSON.stringify(value || {}));
      jsonMode[namespace] = false;
    });
  });
});

function validateJson(namespace, jsonString) {
  try {
    JSON.parse(jsonString);
    errors.value[namespace] = null;
  } catch {
    errors.value[namespace] = "Invalid JSON";
  }
}

function toggleJsonMode(namespace) {
  if (!jsonMode[namespace]) {
    // switching to JSON: serialize current formValues
    editableSettings[namespace] = JSON.stringify(
      formValues[namespace] || {},
      null,
      4,
    );
  } else {
    // switching to form: parse current editableSettings
    try {
      formValues[namespace] = JSON.parse(editableSettings[namespace]);
    } catch {
      return; // don't switch if JSON is invalid
    }
  }
  jsonMode[namespace] = !jsonMode[namespace];
}

async function saveNamespace(namespace) {
  try {
    const parsed = JSON.parse(editableSettings[namespace]);
    await runtimeSettingsStore.update(namespace, parsed);
    await runtimeSettingsStore.getAll();
    errors.value[namespace] = null;
    toastsStore.push(
      `Settings for "${namespace}" updated successfully.`,
      "success",
    );
  } catch {
    errors.value[namespace] = "Invalid JSON";
  }
}

async function saveFormNamespace(namespace) {
  await runtimeSettingsStore.update(namespace, formValues[namespace]);
  await runtimeSettingsStore.getAll();
  editableSettings[namespace] = JSON.stringify(formValues[namespace], null, 4);
  toastsStore.push(
    `Settings for "${namespace}" updated successfully.`,
    "success",
  );
}

// Correlations: CIDR attribute types
const newCidrType = ref("");
function addCidrType(type) {
  if (!type) return;
  const types = formValues.correlations?.possibleCdirAttributeTypes || [];
  if (!types.includes(type)) {
    formValues.correlations.possibleCdirAttributeTypes = [...types, type];
  }
  newCidrType.value = "";
}
function removeCidrType(type) {
  formValues.correlations.possibleCdirAttributeTypes = (
    formValues.correlations.possibleCdirAttributeTypes || []
  ).filter((t) => t !== type);
}

const MATCH_TYPE_OPTIONS = ["term", "cidr"];
const KNOWN_NAMESPACES = ["correlations", "notifications"];
</script>

<template>
  <div class="container mt-4">
    <div class="row justify-content-center">
      <div class="col-md-12">
        <div class="card">
          <div class="card-header">
            <h3>Runtime Settings</h3>
          </div>
          <div class="accordion m-4" id="settingsAccordion">
            <div
              class="accordion-item"
              v-for="namespace in Object.keys(runtimeSettings)"
              :key="namespace"
            >
              <h2 class="accordion-header" :id="`heading_${namespace}`">
                <button
                  class="accordion-button collapsed"
                  type="button"
                  data-bs-toggle="collapse"
                  :data-bs-target="`#collapse_${namespace}`"
                  aria-expanded="false"
                  :aria-controls="`collapse_${namespace}`"
                >
                  <strong>{{ namespace }}</strong>
                </button>
              </h2>

              <div
                :id="`collapse_${namespace}`"
                class="accordion-collapse collapse"
                :aria-labelledby="`heading_${namespace}`"
                data-bs-parent="#settingsAccordion"
              >
                <div class="accordion-body">
                  <!-- Mode toggle (only for known namespaces) -->
                  <div
                    v-if="KNOWN_NAMESPACES.includes(namespace)"
                    class="d-flex justify-content-end mb-3"
                  >
                    <div class="btn-group btn-group-sm" role="group">
                      <button
                        type="button"
                        class="btn"
                        :class="
                          !jsonMode[namespace]
                            ? 'btn-primary'
                            : 'btn-outline-secondary'
                        "
                        @click="jsonMode[namespace] = false"
                      >
                        <FontAwesomeIcon :icon="faSlidersH" class="me-1" />
                        Form
                      </button>
                      <button
                        type="button"
                        class="btn"
                        :class="
                          jsonMode[namespace]
                            ? 'btn-primary'
                            : 'btn-outline-secondary'
                        "
                        @click="toggleJsonMode(namespace)"
                      >
                        <FontAwesomeIcon :icon="faCode" class="me-1" />
                        JSON
                      </button>
                    </div>
                  </div>

                  <!-- ── correlations form ── -->
                  <template
                    v-if="
                      namespace === 'correlations' &&
                      !jsonMode[namespace] &&
                      formValues.correlations
                    "
                  >
                    <div class="row g-3">
                      <div class="col-md-6">
                        <label class="form-label fw-semibold"
                          >Match Types</label
                        >
                        <div>
                          <div
                            v-for="opt in MATCH_TYPE_OPTIONS"
                            :key="opt"
                            class="form-check"
                          >
                            <input
                              class="form-check-input"
                              type="checkbox"
                              :id="`matchType_${opt}`"
                              :value="opt"
                              v-model="formValues.correlations.matchTypes"
                            />
                            <label
                              class="form-check-label"
                              :for="`matchType_${opt}`"
                              >{{ opt }}</label
                            >
                          </div>
                        </div>
                      </div>

                      <div class="col-md-6">
                        <label
                          class="form-label fw-semibold"
                          for="fuzzynessAlgo"
                          >Fuzziness Algorithm</label
                        >
                        <select
                          id="fuzzynessAlgo"
                          class="form-select"
                          :value="formValues.correlations.fuzzynessAlgo"
                          @change="
                            formValues.correlations.fuzzynessAlgo =
                              $event.target.value === '__custom__'
                                ? 1
                                : $event.target.value
                          "
                        >
                          <option value="AUTO">AUTO</option>
                          <option value="0">0</option>
                          <option value="1">1</option>
                          <option value="2">2</option>
                          <option
                            v-if="
                              !['AUTO', '0', '1', '2'].includes(
                                String(formValues.correlations.fuzzynessAlgo),
                              )
                            "
                            :value="formValues.correlations.fuzzynessAlgo"
                          >
                            {{ formValues.correlations.fuzzynessAlgo }}
                          </option>
                        </select>
                        <div class="form-text">
                          AUTO, 0, or a positive integer (max edit distance).
                        </div>
                      </div>

                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="maxCorrelations"
                          >Max Correlations per Doc</label
                        >
                        <input
                          id="maxCorrelations"
                          type="number"
                          class="form-control"
                          v-model.number="
                            formValues.correlations.maxCorrelationsPerDoc
                          "
                        />
                      </div>

                      <div class="col-md-4">
                        <label class="form-label fw-semibold" for="prefixLength"
                          >Prefix Length</label
                        >
                        <input
                          id="prefixLength"
                          type="number"
                          class="form-control"
                          v-model.number="formValues.correlations.prefixLength"
                        />
                      </div>

                      <div class="col-md-4">
                        <label class="form-label fw-semibold" for="minScore"
                          >Min Score</label
                        >
                        <input
                          id="minScore"
                          type="number"
                          class="form-control"
                          v-model.number="formValues.correlations.minScore"
                        />
                      </div>

                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="flushBulkSize"
                          >OpenSearch Flush Bulk Size</label
                        >
                        <input
                          id="flushBulkSize"
                          type="number"
                          class="form-control"
                          v-model.number="
                            formValues.correlations.opensearchFlushBulkSize
                          "
                        />
                      </div>

                      <div class="col-12">
                        <label class="form-label fw-semibold"
                          >Possible CIDR Attribute Types</label
                        >
                        <ul class="list-group mb-2">
                          <li
                            v-for="type in formValues.correlations
                              .possibleCdirAttributeTypes"
                            :key="type"
                            class="list-group-item d-flex justify-content-between align-items-center"
                          >
                            <code class="small">{{ type }}</code>
                            <button
                              type="button"
                              class="btn btn-outline-danger btn-sm"
                              title="Remove"
                              @click="removeCidrType(type)"
                            >
                              <FontAwesomeIcon :icon="faTrash" />
                            </button>
                          </li>
                        </ul>
                        <AttributeTypeSelect
                          name="newCidrType"
                          :selected="newCidrType"
                          @attribute-type-updated="addCidrType"
                        />
                      </div>
                    </div>

                    <div class="d-flex justify-content-end mt-3">
                      <button
                        class="btn btn-primary btn-sm"
                        @click="saveFormNamespace('correlations')"
                      >
                        Save
                      </button>
                    </div>
                  </template>

                  <!-- ── notifications form ── -->
                  <template
                    v-else-if="
                      namespace === 'notifications' &&
                      !jsonMode[namespace] &&
                      formValues.notifications
                    "
                  >
                    <div class="row g-3">
                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="emailMaxPerHour"
                          >Max Notification Emails per Hour</label
                        >
                        <input
                          id="emailMaxPerHour"
                          type="number"
                          class="form-control"
                          v-model.number="
                            formValues.notifications.email_max_per_hour
                          "
                        />
                        <div class="form-text">
                          Set to 0 to disable the limit.
                        </div>
                      </div>
                    </div>

                    <div class="d-flex justify-content-end mt-3">
                      <button
                        class="btn btn-primary btn-sm"
                        @click="saveFormNamespace('notifications')"
                      >
                        Save
                      </button>
                    </div>
                  </template>

                  <!-- ── raw JSON (JSON mode or unknown namespaces) ── -->
                  <template v-else>
                    <textarea
                      v-model="editableSettings[namespace]"
                      class="form-control font-monospace text-sm"
                      spellcheck="false"
                      :rows="
                        editableSettings[namespace]?.split('\n').length || 5
                      "
                      :class="{ 'is-invalid': errors[namespace] }"
                      @input="
                        validateJson(namespace, editableSettings[namespace])
                      "
                    />
                    <div class="invalid-feedback">{{ errors[namespace] }}</div>
                    <div class="d-flex justify-content-end mt-2">
                      <button
                        class="btn btn-primary btn-sm"
                        :disabled="!!errors[namespace]"
                        @click="saveNamespace(namespace)"
                      >
                        <FontAwesomeIcon
                          :icon="faSync"
                          spin
                          v-if="status.loading"
                        />
                        <span v-else>Save</span>
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <Spinner v-if="status.loading" />
</template>
