<script setup>
import { ref, reactive, computed, onMounted } from "vue";
import { storeToRefs } from "pinia";
import { Modal } from "bootstrap";
import Spinner from "@/components/misc/Spinner.vue";
import RetentionConfirmModal from "./RetentionConfirmModal.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import ScheduleEditor from "@/components/tasks/ScheduleEditor.vue";
import {
  useRuntimeSettingsStore,
  useToastsStore,
  useEventsStore,
  useTasksStore,
} from "@/stores";
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
const eventsStore = useEventsStore();
const tasksStore = useTasksStore();
const { runtimeSettings, status } = storeToRefs(runtimeSettingsStore);

const errors = ref({});
const editableSettings = reactive({});
const jsonMode = reactive({});
const formValues = reactive({});

const retentionConfirmModalRef = ref(null);
let retentionConfirmModal = null;

onMounted(() => {
  runtimeSettingsStore.getAll().then(() => {
    Object.entries(runtimeSettings.value).forEach(([namespace, value]) => {
      editableSettings[namespace] = JSON.stringify(value || {}, null, 4);
      formValues[namespace] = JSON.parse(JSON.stringify(value || {}));
      jsonMode[namespace] = false;
    });
  });
  retentionConfirmModal = new Modal(retentionConfirmModalRef.value.$el);
  loadRetentionSchedule();
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
  try {
    await runtimeSettingsStore.update(namespace, formValues[namespace]);
  } catch (error) {
    // e.g. a scoring value the server refuses, which it names.
    toastsStore.push(`Could not save "${namespace}": ${error}`, "danger");
    return;
  }
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

const MATCH_TYPE_OPTIONS = ["term", "cidr", "ja4"];
const KNOWN_NAMESPACES = [
  "correlations",
  "exports",
  "notifications",
  "retention",
  "scoring",
];

// Scoring: per-type half-lives, edited as rows.
const SCORE_SOURCES = ["local", "server", "feed", "unknown"];
const SCORE_NUMBERS = [
  [
    "default_half_life_days",
    "Default half-life (days)",
    "Types not listed below. 0 never decays.",
  ],
  [
    "corroboration_per_source",
    "Per further source",
    "Added for each further independent source.",
  ],
  [
    "corroboration_max",
    "Corroboration cap",
    "At most this much from further sources.",
  ],
  [
    "sighting_boost_max",
    "Sightings boost cap",
    "Positive sightings add 5, 10, 15... up to this.",
  ],
  [
    "false_positive_penalty",
    "Per false positive",
    "Taken off per false-positive sighting.",
  ],
  [
    "false_positive_penalty_max",
    "False-positive cap",
    "At most this much from false positives.",
  ],
  [
    "warninglist_penalty",
    "Warninglist penalty",
    "Taken off when on an enabled warninglist.",
  ],
  [
    "expiration_cap",
    "Expired score cap",
    "An expiration sighting newer than any positive one caps the score here.",
  ],
  [
    "decayed_below",
    "Decayed below",
    "Below this an indicator counts as decayed (restSearch excludeDecayed).",
  ],
  [
    "refresh_step",
    "Refresh step",
    "A stored score is rewritten when it moves this much (or crosses Decayed below).",
  ],
];
const ADAPTIVE_NUMBERS = [
  [
    "adaptive_window_days",
    "Window (days)",
    "False positives and sightings this recent count, here and in source quality.",
  ],
  [
    "adaptive_min_indicators",
    "Minimum indicators",
    "Sources with fewer indicators are left alone.",
  ],
  [
    "adaptive_points_per_percent",
    "Points per percent",
    "Taken off per percent of a source's indicators reported benign.",
  ],
  [
    "adaptive_max_penalty",
    "Maximum penalty",
    "Adaptive trust never takes off more than this.",
  ],
];
const newHalfLifeType = ref("");
const newHalfLifeDays = ref(30);
function addHalfLife(type) {
  if (!type) return;
  formValues.scoring.half_life_days = {
    ...(formValues.scoring.half_life_days || {}),
    [type]: Number(newHalfLifeDays.value) || 0,
  };
  newHalfLifeType.value = "";
}
function removeHalfLife(type) {
  const rest = { ...formValues.scoring.half_life_days };
  delete rest[type];
  formValues.scoring.half_life_days = rest;
}

// Retention: bridge string[] ↔ tag objects for TagsSelect
const exemptTagObjects = computed(() =>
  (formValues.retention?.exempt_tags || []).map((name) => ({
    id: null,
    name,
    colour: "#6c757d",
  })),
);

function onExemptTagsChanged(tagNames) {
  formValues.retention.exempt_tags = tagNames;
}

const retentionPreviewCount = ref(0);

async function saveRetention() {
  const count = await eventsStore.retentionPreview(
    formValues.retention.period_days,
  );
  retentionPreviewCount.value = count.count;
  retentionConfirmModal.show();
}

function confirmRetention() {
  saveFormNamespace("retention");
  retentionConfirmModal.hide();
}

// Retention: scheduled job
const RETENTION_TASK_NAME = "app.worker.tasks.enforce_retention";
const retentionSchedule = ref(null);
const retentionScheduleEditor = ref(null);
const retentionScheduleValid = ref(false);
const retentionScheduleSaving = ref(false);

async function loadRetentionSchedule() {
  await tasksStore.get_scheduled_tasks();
  retentionSchedule.value =
    tasksStore.scheduledTasks.find(
      (t) => t.task_name === RETENTION_TASK_NAME,
    ) || null;
}

async function createRetentionSchedule() {
  retentionScheduleSaving.value = true;
  const editor = retentionScheduleEditor.value;
  if (!editor) {
    retentionScheduleSaving.value = false;
    return;
  }
  const result = await tasksStore.create_scheduled_task({
    task_name: RETENTION_TASK_NAME,
    params: {},
    schedule: editor.buildSchedule(),
    enabled: true,
  });
  if (result) {
    toastsStore.push("Retention job scheduled.", "success");
    await loadRetentionSchedule();
  }
  retentionScheduleSaving.value = false;
}

async function deleteRetentionSchedule() {
  if (!retentionSchedule.value) return;
  retentionScheduleSaving.value = true;
  await tasksStore.delete_scheduled_task(retentionSchedule.value.id);
  retentionSchedule.value = null;
  retentionScheduleEditor.value?.reset();
  toastsStore.push("Retention schedule removed.", "success");
  retentionScheduleSaving.value = false;
}
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
                      <div class="col-12">
                        <div class="form-check form-switch">
                          <input
                            class="form-check-input"
                            type="checkbox"
                            id="correlateOnChange"
                            v-model="formValues.correlations.correlateOnChange"
                          />
                          <label
                            class="form-check-label fw-semibold"
                            for="correlateOnChange"
                          >
                            Correlate on Change
                          </label>
                        </div>
                        <div class="form-text">
                          When enabled, attributes are correlated in a
                          background task as soon as they are created or their
                          value changes, instead of waiting for the next full
                          correlation run.
                        </div>
                      </div>

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

                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="msearchChunkSize"
                          >OpenSearch Multi-Search Chunk Size</label
                        >
                        <input
                          id="msearchChunkSize"
                          type="number"
                          class="form-control"
                          v-model.number="
                            formValues.correlations.msearchChunkSize
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

                  <!-- ── scoring form ── -->
                  <template
                    v-else-if="
                      namespace === 'scoring' &&
                      !jsonMode[namespace] &&
                      formValues.scoring
                    "
                  >
                    <p class="text-muted small">
                      Every consolidated indicator gets a confidence score from
                      0 to 100: its best source's base, minus decay since it was
                      last seen, plus sightings, minus false positives and
                      warninglist hits. Saving re-scores all indicators.
                    </p>
                    <div class="form-check form-switch mb-3">
                      <input
                        id="scoringEnabled"
                        class="form-check-input"
                        type="checkbox"
                        v-model="formValues.scoring.enabled"
                      />
                      <label class="form-check-label" for="scoringEnabled"
                        >Score indicators</label
                      >
                    </div>

                    <h6 class="fw-semibold">Base score by source</h6>
                    <div class="row g-3 mb-3">
                      <div
                        v-for="source in SCORE_SOURCES"
                        :key="source"
                        class="col-6 col-md-3"
                      >
                        <label
                          class="form-label"
                          :for="`scoringBase-${source}`"
                          >{{ source }}</label
                        >
                        <input
                          :id="`scoringBase-${source}`"
                          type="number"
                          min="0"
                          max="100"
                          class="form-control"
                          v-model.number="
                            formValues.scoring.base_by_source[source]
                          "
                        />
                      </div>
                    </div>

                    <h6 class="fw-semibold">Half-life by attribute type</h6>
                    <div class="form-text mb-2">
                      Days for the score to halve, counted from last seen (which
                      positive sightings move). 0 never decays.
                    </div>
                    <table class="table table-sm align-middle mb-2">
                      <tbody>
                        <tr
                          v-for="(days, type) in formValues.scoring
                            .half_life_days"
                          :key="type"
                        >
                          <td>
                            <code class="small">{{ type }}</code>
                          </td>
                          <td style="width: 10em">
                            <input
                              type="number"
                              min="0"
                              class="form-control form-control-sm"
                              :aria-label="`Half-life of ${type} in days`"
                              v-model.number="
                                formValues.scoring.half_life_days[type]
                              "
                            />
                          </td>
                          <td class="text-end" style="width: 3em">
                            <button
                              type="button"
                              class="btn btn-outline-danger btn-sm"
                              title="Remove"
                              @click="removeHalfLife(type)"
                            >
                              <FontAwesomeIcon :icon="faTrash" />
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                    <div class="row g-2 align-items-center mb-3">
                      <div class="col-md-3">
                        <input
                          type="number"
                          min="0"
                          class="form-control"
                          v-model.number="newHalfLifeDays"
                          aria-label="Half-life in days for the type to add"
                          title="Days, for the type picked next"
                        />
                      </div>
                      <div class="col-md-9">
                        <AttributeTypeSelect
                          name="newHalfLifeType"
                          :selected="newHalfLifeType"
                          @attribute-type-updated="addHalfLife"
                        />
                      </div>
                    </div>

                    <h6 class="fw-semibold">Adaptive trust</h6>
                    <div class="form-check form-switch mb-1">
                      <input
                        id="scoringAdaptiveTrust"
                        class="form-check-input"
                        type="checkbox"
                        v-model="formValues.scoring.adaptive_trust"
                      />
                      <label class="form-check-label" for="scoringAdaptiveTrust"
                        >Lower the trust of sources whose indicators are
                        reported benign</label
                      >
                    </div>
                    <div class="form-text mb-2">
                      Off by default: anyone who can report sightings can report
                      false positives against a source. Source quality shows
                      what it would take off either way.
                    </div>
                    <div class="row g-3 mb-3">
                      <div
                        v-for="[key, label, help] in ADAPTIVE_NUMBERS"
                        :key="key"
                        class="col-md-3"
                      >
                        <label class="form-label" :for="`scoring-${key}`">{{
                          label
                        }}</label>
                        <input
                          :id="`scoring-${key}`"
                          type="number"
                          min="0"
                          class="form-control"
                          v-model.number="formValues.scoring[key]"
                        />
                        <div class="form-text">{{ help }}</div>
                      </div>
                    </div>

                    <h6 class="fw-semibold">Adjustments and thresholds</h6>
                    <div class="row g-3">
                      <div
                        v-for="[key, label, help] in SCORE_NUMBERS"
                        :key="key"
                        class="col-md-4"
                      >
                        <label class="form-label" :for="`scoring-${key}`">{{
                          label
                        }}</label>
                        <input
                          :id="`scoring-${key}`"
                          type="number"
                          min="0"
                          class="form-control"
                          v-model.number="formValues.scoring[key]"
                        />
                        <div class="form-text">{{ help }}</div>
                      </div>
                    </div>

                    <div class="d-flex justify-content-end mt-3">
                      <button
                        class="btn btn-primary btn-sm"
                        @click="saveFormNamespace('scoring')"
                      >
                        Save
                      </button>
                    </div>
                  </template>

                  <!-- ── exports form ── -->
                  <template
                    v-else-if="
                      namespace === 'exports' &&
                      !jsonMode[namespace] &&
                      formValues.exports
                    "
                  >
                    <div class="row g-3">
                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="exportsMaxConcurrentPerUser"
                          >Max Concurrent Exports per User</label
                        >
                        <input
                          id="exportsMaxConcurrentPerUser"
                          type="number"
                          min="0"
                          class="form-control"
                          v-model.number="
                            formValues.exports.max_concurrent_per_user
                          "
                        />
                        <div class="form-text">
                          Streaming exports a user can run at once; further
                          requests get a 429. Set to 0 to disable the limit.
                        </div>
                      </div>
                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="exportsDeltaRetention"
                          >Deltas Kept per Incremental Feed</label
                        >
                        <input
                          id="exportsDeltaRetention"
                          type="number"
                          min="1"
                          class="form-control"
                          v-model.number="formValues.exports.delta_retention"
                        />
                        <div class="form-text">
                          A consumer further behind than the oldest kept delta
                          has to download the full feed again.
                        </div>
                      </div>
                    </div>

                    <div class="d-flex justify-content-end mt-3">
                      <button
                        class="btn btn-primary btn-sm"
                        @click="saveFormNamespace('exports')"
                      >
                        Save
                      </button>
                    </div>
                  </template>

                  <!-- ── retention form ── -->
                  <template
                    v-else-if="
                      namespace === 'retention' &&
                      !jsonMode[namespace] &&
                      formValues.retention
                    "
                  >
                    <div class="row g-3">
                      <div class="col-md-4">
                        <div class="form-check form-switch">
                          <input
                            class="form-check-input"
                            type="checkbox"
                            id="retentionEnabled"
                            v-model="formValues.retention.enabled"
                          />
                          <label
                            class="form-check-label fw-semibold"
                            for="retentionEnabled"
                          >
                            Enabled
                          </label>
                        </div>
                        <div class="form-text">
                          When enabled, events older than the retention period
                          will be eligible for soft-deletion.
                        </div>
                      </div>

                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="retentionPeriodDays"
                        >
                          Retention Period (days)
                        </label>
                        <input
                          id="retentionPeriodDays"
                          type="number"
                          class="form-control"
                          min="1"
                          v-model.number="formValues.retention.period_days"
                        />
                      </div>

                      <div class="col-md-4">
                        <label
                          class="form-label fw-semibold"
                          for="retentionWarningDays"
                        >
                          Warning Days
                        </label>
                        <input
                          id="retentionWarningDays"
                          type="number"
                          class="form-control"
                          min="0"
                          v-model.number="formValues.retention.warning_days"
                        />
                        <div class="form-text">
                          Show a warning badge on events within this many days
                          of expiry.
                        </div>
                      </div>

                      <div class="col-12">
                        <label class="form-label fw-semibold"
                          >Exempt Tags</label
                        >
                        <div class="form-text mb-2">
                          Events with any of these tags are excluded from
                          retention.
                        </div>
                        <TagsSelect
                          modelClass="event"
                          :persist="false"
                          :selectedTags="exemptTagObjects"
                          @update:selectedTags="onExemptTagsChanged"
                        />
                      </div>
                    </div>

                    <div class="d-flex justify-content-end mt-3">
                      <button
                        class="btn btn-primary btn-sm"
                        @click="saveRetention"
                      >
                        Save
                      </button>
                    </div>

                    <hr />

                    <h6 class="fw-semibold">Scheduled Job</h6>

                    <div
                      v-if="retentionSchedule"
                      class="alert alert-info small mb-0"
                    >
                      Active schedule:
                      <strong>{{ retentionSchedule.schedule }}</strong>
                      <span v-if="retentionSchedule.last_run_at">
                        &mdash; last run:
                        {{ retentionSchedule.last_run_at }}
                      </span>
                      <div class="mt-2">
                        <button
                          class="btn btn-outline-danger btn-sm"
                          :disabled="retentionScheduleSaving"
                          @click="deleteRetentionSchedule"
                        >
                          Remove Schedule
                        </button>
                      </div>
                    </div>

                    <template v-else>
                      <div class="form-text mb-3">
                        Schedule the retention enforcement task to run
                        automatically.
                      </div>

                      <ScheduleEditor
                        :ref="
                          (el) => {
                            retentionScheduleEditor = el;
                          }
                        "
                        :initial-schedule="{
                          type: 'crontab',
                          minute: '0',
                          hour: '2',
                          dayOfMonth: '*',
                          month: '*',
                          dayOfWeek: '*',
                        }"
                        @valid-change="retentionScheduleValid = $event"
                      />

                      <div class="d-flex justify-content-end mt-3">
                        <button
                          class="btn btn-primary btn-sm"
                          :disabled="
                            !retentionScheduleValid || retentionScheduleSaving
                          "
                          @click="createRetentionSchedule"
                        >
                          Create Schedule
                        </button>
                      </div>
                    </template>
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

  <RetentionConfirmModal
    ref="retentionConfirmModalRef"
    :period-days="formValues.retention?.period_days"
    :affected-count="retentionPreviewCount"
    @confirmed="confirmRetention"
  />

  <Spinner v-if="status.loading" />
</template>
