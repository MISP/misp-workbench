<script setup>
import { ref, reactive, computed, shallowRef, onMounted } from "vue";
import { router } from "@/router";
import { useReactorStore, useToastsStore } from "@/stores";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import { faPlay, faPlus, faXmark } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import TriggerFiltersEditor from "@/components/reactor/TriggerFiltersEditor.vue";

const props = defineProps({
  mode: {
    type: String,
    default: "add",
    validator: (v) => ["add", "edit"].includes(v),
  },
  scriptId: { type: [String, Number], default: null },
});

const reactorStore = useReactorStore();
const toastsStore = useToastsStore();

const RESOURCE_OPTIONS = [
  "event",
  "attribute",
  "object",
  "correlation",
  "sighting",
];
const ACTION_OPTIONS = [
  "created",
  "updated",
  "deleted",
  "published",
  "unpublished",
];

const DEFAULT_SOURCE = `def handle(ctx, payload, trigger):
    """Called for every matching trigger.

    \`\`ctx\`\` exposes get_event/get_attribute/add_attribute/tag_event/tag_attribute.
    \`\`payload\`\` is the entity the trigger fired on (dict).
    \`\`trigger\`\` is {"resource_type": ..., "action": ...} for the firing trigger.
    """
    ctx.log("trigger", trigger, "payload", payload)
`;

const triggerCardId = Math.random().toString(36).substring(2, 8);

const script = reactive({
  name: "",
  description: "",
  entrypoint: "handle",
  status: "active",
  timeout_seconds: 60,
  max_writes: 100,
  source: props.mode === "edit" ? "" : DEFAULT_SOURCE,
});

const triggers = ref(
  props.mode === "edit"
    ? []
    : [{ resource_type: "attribute", action: "created", filters: {} }],
);

const loaded = ref(props.mode === "add");
const savedScriptId = ref(props.mode === "edit" ? props.scriptId : null);

onMounted(async () => {
  if (props.mode !== "edit" || !props.scriptId) return;
  const detail = await reactorStore.getById(props.scriptId);
  Object.assign(script, {
    name: detail.name,
    description: detail.description ?? "",
    entrypoint: detail.entrypoint,
    status: detail.status,
    timeout_seconds: detail.timeout_seconds,
    max_writes: detail.max_writes,
  });
  triggers.value = (detail.triggers || []).map((t) => ({
    resource_type: t.resource_type,
    action: t.action,
    filters: t.filters || {},
  }));
  if (triggers.value.length === 0) {
    triggers.value.push({
      resource_type: "attribute",
      action: "created",
      filters: {},
    });
  }
  const sourceResp = await reactorStore.getSource(props.scriptId);
  script.source = sourceResp.source;
  loaded.value = true;
});

function addTrigger() {
  triggers.value.push({
    resource_type: "attribute",
    action: "created",
    filters: {},
  });
}
function removeTrigger(idx) {
  triggers.value.splice(idx, 1);
  if (selectedTriggerIdx.value >= triggers.value.length) {
    selectedTriggerIdx.value = Math.max(0, triggers.value.length - 1);
  }
}

function filterSummary(filters) {
  if (!filters || !Object.keys(filters).length) return "no filters";
  const parts = [];
  if (filters.tags?.length) parts.push(`tags: ${filters.tags.join(", ")}`);
  if (filters.orgs?.length) parts.push(`orgs: ${filters.orgs.join(", ")}`);
  if (filters.types?.length) parts.push(`types: ${filters.types.join(", ")}`);
  if (filters.templates?.length)
    parts.push(`templates: ${filters.templates.join(", ")}`);
  const handled = new Set(["tags", "orgs", "types", "templates"]);
  const extra = Object.keys(filters).filter((k) => !handled.has(k));
  if (extra.length) parts.push(`+${extra.length} more`);
  return parts.join(" · ") || "no filters";
}

const apiError = ref(null);
const canSubmit = computed(
  () =>
    loaded.value && script.name && script.source && triggers.value.length > 0,
);

const monacoOptions = {
  fontSize: 13,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: "on",
};
const editorRef = shallowRef(null);
function onEditorMount(editor) {
  editorRef.value = editor;
}

function buildScriptPayload() {
  const cleanTriggers = triggers.value.map((t) => ({
    resource_type: t.resource_type,
    action: t.action,
    filters: Object.keys(t.filters || {}).length ? t.filters : null,
  }));
  return { ...script, triggers: cleanTriggers };
}

const submitting = computed(() =>
  props.mode === "edit"
    ? reactorStore.status.updating
    : reactorStore.status.creating,
);

async function submit() {
  apiError.value = null;
  try {
    if (props.mode === "edit") {
      await reactorStore.update(props.scriptId, buildScriptPayload());
      toastsStore.push(`Reactor script "${script.name}" updated.`, "success");
      router.push(`/tech-lab/reactor/${props.scriptId}`);
    } else {
      const response = await reactorStore.create(buildScriptPayload());
      toastsStore.push(`Reactor script "${response.name}" created.`, "success");
      router.push(`/tech-lab/reactor/${response.id}`);
    }
  } catch (err) {
    apiError.value = err?.message || String(err);
  }
}

function cancel() {
  if (props.mode === "edit" && props.scriptId) {
    router.push(`/tech-lab/reactor/${props.scriptId}`);
  } else {
    router.push("/tech-lab/reactor");
  }
}

const testPayloadText = ref("{}");
const testRun = ref(null);
const testLog = ref(null);
const testError = ref(null);
const selectedTriggerIdx = ref(0);

const selectedTrigger = computed(() => {
  const t = triggers.value[selectedTriggerIdx.value];
  return t ? { resource_type: t.resource_type, action: t.action } : null;
});

const SAMPLE_PAYLOADS = {
  event: {
    event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    info: "Sample phishing campaign",
    distribution: 1,
    threat_level_id: 2,
    analysis: 1,
    date: "2026-05-01",
    published: false,
    orgc: { name: "CIRCL", uuid: "55f6ea5e-2c60-40e5-964f-47a8950d210f" },
    org: { name: "CIRCL", uuid: "55f6ea5e-2c60-40e5-964f-47a8950d210f" },
    tags: [
      { name: "tlp:white", colour: "#ffffff" },
      { name: "type:OSINT", colour: "#3a87ad" },
    ],
    attribute_count: 2,
  },
  attribute: {
    event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    attribute_uuid: "9aa1b6f0-1a55-4e7f-b40f-2bf5b4c83c12",
    object_uuid: null,
    type: "ip-src",
    category: "Network activity",
    value: "198.51.100.42",
    to_ids: true,
    distribution: 5,
    comment: "C2 server",
    timestamp: 1714579200,
    tags: [{ name: "tlp:amber", colour: "#ffc107" }],
  },
  object: {
    event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    object_uuid: "0b53a3a4-cf2a-4bb7-9210-29f0aebf8c10",
    name: "file",
    template_uuid: "688c46fb-5edb-40a3-8273-1af7923e2215",
    template_version: 24,
    description: "Suspicious dropper",
    meta_category: "file",
    distribution: 5,
    timestamp: 1714579200,
    attributes: [
      {
        attribute_uuid: "f3a91d29-3711-4d8b-83a5-6b4f9d1f2a02",
        type: "filename",
        value: "invoice.exe",
      },
      {
        attribute_uuid: "21cf6a5b-b6a0-4632-8db8-21a4c3a3d9e3",
        type: "sha256",
        value:
          "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      },
    ],
  },
  correlation: {
    source_attribute_uuid: "9aa1b6f0-1a55-4e7f-b40f-2bf5b4c83c12",
    source_event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    target_event_uuid: "7c8b8b2c-99e3-4f5b-9d1e-2f1c8e6a5d40",
    target_attribute_uuid: "b1f0e9c4-72e2-4be4-9a67-9d6e6d6f2b3c",
    target_attribute_type: "ip-src",
    target_attribute_value: "198.51.100.42",
  },
  sighting: {
    type: 0,
    value: "198.51.100.42",
    organisation: "CIRCL",
    timestamp: 1714579200,
  },
};

function loadSample(resource) {
  const sample = SAMPLE_PAYLOADS[resource];
  if (!sample) return;
  testPayloadText.value = JSON.stringify(sample, null, 2);
}

async function runTest() {
  apiError.value = null;
  testError.value = null;
  testRun.value = null;
  testLog.value = null;
  if (!canSubmit.value) {
    testError.value = "Set a name and at least one trigger first.";
    return;
  }
  let parsedPayload;
  try {
    parsedPayload = JSON.parse(testPayloadText.value || "{}");
  } catch (e) {
    testError.value = `Invalid payload JSON: ${e.message}`;
    return;
  }
  try {
    const result = await reactorStore.saveAndTest({
      scriptId: savedScriptId.value,
      scriptPayload: buildScriptPayload(),
      testPayload: parsedPayload,
      trigger: selectedTrigger.value,
    });
    savedScriptId.value = result.scriptId;
    testRun.value = result.run;
    testLog.value = result.log;
  } catch (err) {
    testError.value = err?.message || String(err);
  }
}
</script>

<template>
  <div class="container-fluid px-0" v-if="loaded">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div>
        <h4 class="mb-0">
          {{ mode === "edit" ? "Edit Reactor Script" : "New Reactor Script" }}
        </h4>
        <small class="text-muted">
          Reacts to a trigger and runs in an isolated worker. Writes go through
          the audit log.
        </small>
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-secondary" @click="cancel">
          Cancel
        </button>
        <button
          class="btn btn-primary"
          :disabled="!canSubmit || submitting"
          @click="submit"
        >
          <template v-if="mode === 'edit'">
            {{ submitting ? "Saving…" : "Save" }}
          </template>
          <template v-else>
            {{ submitting ? "Creating…" : "Create" }}
          </template>
        </button>
      </div>
    </div>

    <div class="card mb-3">
      <div class="card-body">
        <div class="mb-3">
          <label class="form-label" for="r-name">Name</label>
          <input
            id="r-name"
            class="form-control form-control-sm"
            v-model="script.name"
          />
        </div>
        <div class="mb-0">
          <label class="form-label" for="r-desc">Description</label>
          <textarea
            id="r-desc"
            class="form-control form-control-sm"
            rows="2"
            v-model="script.description"
          />
        </div>

        <div class="mt-3">
          <label class="form-label">Triggers</label>
          <div
            v-for="(t, idx) in triggers"
            :key="idx"
            class="border rounded mb-2"
          >
            <div class="d-flex gap-2 align-items-center p-2">
              <select
                v-model="t.resource_type"
                class="form-select form-select-sm"
                style="max-width: 160px"
              >
                <option v-for="r in RESOURCE_OPTIONS" :key="r" :value="r">
                  {{ r }}
                </option>
              </select>
              <select
                v-model="t.action"
                class="form-select form-select-sm"
                style="max-width: 160px"
              >
                <option v-for="a in ACTION_OPTIONS" :key="a" :value="a">
                  {{ a }}
                </option>
              </select>
              <button
                class="btn btn-outline-danger btn-sm ms-auto"
                @click="removeTrigger(idx)"
                :disabled="triggers.length === 1"
                title="remove trigger"
              >
                <FontAwesomeIcon :icon="faXmark" />
              </button>
            </div>
            <div
              class="accordion accordion-flush"
              :id="`trigger-acc-${triggerCardId}-${idx}`"
            >
              <div class="accordion-item">
                <h2
                  class="accordion-header"
                  :id="`trigger-h-${triggerCardId}-${idx}`"
                >
                  <button
                    class="accordion-button collapsed py-2 small"
                    type="button"
                    data-bs-toggle="collapse"
                    :data-bs-target="`#trigger-c-${triggerCardId}-${idx}`"
                    aria-expanded="false"
                    :aria-controls="`trigger-c-${triggerCardId}-${idx}`"
                  >
                    Filters
                    <span class="ms-2 text-muted">
                      ({{ filterSummary(t.filters) }})
                    </span>
                  </button>
                </h2>
                <div
                  :id="`trigger-c-${triggerCardId}-${idx}`"
                  class="accordion-collapse collapse"
                  :aria-labelledby="`trigger-h-${triggerCardId}-${idx}`"
                  :data-bs-parent="`#trigger-acc-${triggerCardId}-${idx}`"
                >
                  <div class="accordion-body">
                    <TriggerFiltersEditor
                      :key="`${idx}-${t.resource_type}`"
                      :modelClass="t.resource_type"
                      :resourceType="t.resource_type"
                      v-model="t.filters"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <button class="btn btn-outline-secondary btn-sm" @click="addTrigger">
            <FontAwesomeIcon :icon="faPlus" class="me-1" />
            add trigger
          </button>
        </div>

        <div class="row g-3 mt-1">
          <div class="col-md-3">
            <label class="form-label" for="r-entry">Entrypoint</label>
            <input
              id="r-entry"
              class="form-control form-control-sm"
              v-model="script.entrypoint"
            />
          </div>
          <div class="col-md-3">
            <label class="form-label" for="r-timeout">Timeout (s)</label>
            <input
              id="r-timeout"
              type="number"
              class="form-control form-control-sm"
              v-model.number="script.timeout_seconds"
              min="1"
              max="600"
            />
          </div>
          <div class="col-md-3">
            <label class="form-label" for="r-writes">Max writes / run</label>
            <input
              id="r-writes"
              type="number"
              class="form-control form-control-sm"
              v-model.number="script.max_writes"
              min="0"
            />
          </div>
          <div class="col-md-3 d-flex align-items-end">
            <div class="form-check form-switch mb-2">
              <input
                class="form-check-input"
                type="checkbox"
                role="switch"
                id="r-active"
                :checked="script.status === 'active'"
                @change="
                  script.status = $event.target.checked ? 'active' : 'paused'
                "
              />
              <label class="form-check-label" for="r-active">Active</label>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="apiError" class="alert alert-danger">{{ apiError }}</div>

    <div class="row g-3">
      <div class="col-lg-7">
        <div class="card h-100">
          <div
            class="card-header d-flex justify-content-between align-items-center"
          >
            <span>Source</span>
            <small class="text-muted font-monospace">python</small>
          </div>
          <div class="card-body p-0">
            <VueMonacoEditor
              v-model:value="script.source"
              language="python"
              theme="vs-dark"
              :options="monacoOptions"
              :height="`520px`"
              @mount="onEditorMount"
            />
          </div>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="card h-100">
          <div
            class="card-header d-flex justify-content-between align-items-center"
          >
            <span>Test sandbox</span>
            <button
              class="btn btn-primary btn-sm"
              :disabled="reactorStore.status.testing"
              @click="runTest"
            >
              <FontAwesomeIcon :icon="faPlay" class="me-1" />
              {{ reactorStore.status.testing ? "Running…" : "Run" }}
            </button>
          </div>
          <div class="card-body d-flex flex-column" style="min-height: 520px">
            <label class="form-label small mb-1">Trigger</label>
            <select
              class="form-select form-select-sm mb-3"
              v-model.number="selectedTriggerIdx"
            >
              <option
                v-for="(t, idx) in triggers"
                :key="`${idx}-${t.resource_type}-${t.action}`"
                :value="idx"
              >
                {{ t.resource_type }}.{{ t.action }}
              </option>
            </select>

            <div class="d-flex justify-content-between align-items-center mb-1">
              <label class="form-label small mb-0">Payload (JSON)</label>
              <div class="dropdown">
                <button
                  class="btn btn-outline-secondary btn-sm dropdown-toggle"
                  type="button"
                  data-bs-toggle="dropdown"
                  aria-expanded="false"
                >
                  Load sample
                </button>
                <ul class="dropdown-menu dropdown-menu-end">
                  <li v-for="r in RESOURCE_OPTIONS" :key="r">
                    <a
                      class="dropdown-item small"
                      href="#"
                      @click.prevent="loadSample(r)"
                    >
                      {{ r }}
                    </a>
                  </li>
                </ul>
              </div>
            </div>
            <textarea
              class="form-control font-monospace small mb-3"
              rows="6"
              v-model="testPayloadText"
              spellcheck="false"
            />

            <div v-if="testError" class="alert alert-warning small mb-2">
              {{ testError }}
            </div>

            <div v-if="testRun" class="mb-2 small">
              <span class="me-2">Status:</span>
              <span
                class="badge"
                :class="
                  testRun.status === 'success'
                    ? 'bg-success'
                    : testRun.status === 'failed' ||
                        testRun.status === 'timed_out'
                      ? 'bg-danger'
                      : 'bg-secondary'
                "
              >
                {{ testRun.status }}
              </span>
              <span class="ms-3 text-muted">
                writes: {{ testRun.writes_count }}
              </span>
              <span v-if="savedScriptId" class="ms-3 text-muted">
                script #{{ savedScriptId }} (saved)
              </span>
            </div>

            <label class="form-label small mb-1">Log</label>
            <pre
              class="p-2 small mb-0 flex-grow-1"
              style="
                background: #1e1e1e;
                color: #d4d4d4;
                overflow: auto;
                min-height: 180px;
                white-space: pre-wrap;
              "
              >{{
                testLog === null
                  ? "(run to see log output)"
                  : testLog || "(empty)"
              }}</pre
            >
          </div>
        </div>
      </div>
    </div>

    <p class="text-muted small mt-2 mb-0">
      Note: clicking "Run" saves the script (creating it on first run, updating
      after) and then executes it against your payload.
    </p>
  </div>
</template>
