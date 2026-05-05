<script setup>
import {
  ref,
  reactive,
  computed,
  shallowRef,
  onMounted,
  onBeforeUnmount,
  watch,
} from "vue";
import { router } from "@/router";
import { useReactorStore, useToastsStore } from "@/stores";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import {
  faPlay,
  faPlus,
  faXmark,
  faBook,
} from "@fortawesome/free-solid-svg-icons";
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
  max_writes: 10,
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
  minimap: { enabled: true },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: "on",
};

const ctxExampleOptions = {
  ...monacoOptions,
  readOnly: true,
  lineNumbers: "off",
  glyphMargin: false,
  folding: false,
  minimap: { enabled: false },
  renderLineHighlight: "none",
  contextmenu: false,
};

const EXAMPLE_LIBRARY = {
  Event: [
    {
      title: "Log when an event is published",
      source: `def handle(ctx, payload, trigger):
    if trigger["action"] != "published":
        return
    ctx.log(
        "event published",
        payload.get("event_uuid"),
        "by",
        (payload.get("orgc") or {}).get("name"),
    )
`,
    },
    {
      title: "Migrate tlp:white events to tlp:clear",
      source: `def handle(ctx, payload, trigger):
    """Add tlp:clear to events tagged tlp:white (TLP rename)."""
    tag_names = {
        t.get("name") for t in payload.get("tags", []) if isinstance(t, dict)
    }
    if "tlp:white" in tag_names and "tlp:clear" not in tag_names:
      ctx.tag_event(payload["event_uuid"], "tlp:clear")
      ctx.log("added tlp:clear to", payload["event_uuid"])
`,
    },
  ],
  Attribute: [
    {
      title: "Tag suspicious IPs amber",
      source: `def handle(ctx, payload, trigger):
    if payload.get("type") != "ip-src":
        return
    ctx.tag_attribute(payload["uuid"], "tlp:amber")
`,
    },
    {
      title: "Geolocate ip-src attributes (mmdb_lookup)",
      source: `def handle(ctx, payload, trigger):
    """Resolve geolocation / ASN for new ip-src/ip-dst attributes."""
    if payload.get("type") not in ("ip-src", "ip-dst"):
        return

    result = ctx.enrich(
        value=payload["value"],
        type=payload["type"],
        module="mmdb_lookup",
    )

    # mmdb_lookup returns:
    #   {"results": {"Attribute": [echo], "Object": [
    #     {"name": "geolocation", "Attribute": [{object_relation, value, ...}]},
    #     {"name": "asn", "Attribute": [...]},
    #   ]}}
    for obj in (result.get("results") or {}).get("Object", []):
        for attr in obj.get("Attribute", []):
            relation = attr.get("object_relation") or attr.get("type")
            ctx.log(
                "mmdb_lookup",
                payload["value"],
                f"{obj.get('name')}.{relation}",
                "=",
                attr.get("value"),
            )
`,
    },
  ],
  Object: [
    {
      title: "Log file objects with hashes",
      source: `def handle(ctx, payload, trigger):
    if payload.get("name") != "file":
        return
    hashes = [
        a for a in payload.get("attributes", [])
        if a.get("type") in ("md5", "sha1", "sha256")
    ]
    ctx.log("file object", payload["object_uuid"], "hashes:", hashes)
`,
    },
  ],
  Correlation: [
    {
      title: "Tag both sides of a new correlation",
      source: `def handle(ctx, payload, trigger):
    """Mark both attributes when a fresh correlation appears."""
    ctx.tag_attribute(payload["source_attribute_uuid"], "correlated")
    ctx.tag_attribute(payload["target_attribute_uuid"], "correlated")
`,
    },
  ],
  Sighting: [
    {
      title: "Promote frequently-seen IoCs",
      source: `def handle(ctx, payload, trigger):
    """Bump confidence on attributes that get sighted."""
    ctx.log(
        "sighting",
        payload.get("type"),
        payload.get("value"),
        "by",
        payload.get("organisation"),
    )
`,
    },
  ],
};

const selectedExample = shallowRef(EXAMPLE_LIBRARY.Attribute[0]);
const ctxModalTab = ref("docs"); // "docs" | "library"

function selectExample(example) {
  selectedExample.value = example;
  ctxModalTab.value = "library";
}

function useExampleAsSource() {
  if (!selectedExample.value) return;
  script.source = selectedExample.value.source;
}
const editorRef = shallowRef(null);
function onEditorMount(editor) {
  editorRef.value = editor;
}

function detectMonacoTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "vs-dark"
    : "vs";
}

const monacoTheme = ref(detectMonacoTheme());
let themeObserver = null;

onMounted(() => {
  themeObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.attributeName === "data-bs-theme")) {
      monacoTheme.value = detectMonacoTheme();
    }
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-bs-theme"],
  });
});

onBeforeUnmount(() => {
  themeObserver?.disconnect();
  themeObserver = null;
});

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

const testStorageKey = computed(
  () => `reactor:script:${savedScriptId.value ?? props.scriptId ?? "new"}:test`,
);

let _testStorageHydrated = false;
function loadTestStateFromStorage() {
  try {
    const raw = localStorage.getItem(testStorageKey.value);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (typeof data.payload === "string") {
      testPayloadText.value = data.payload;
    }
    if (data.trigger?.resource_type && data.trigger?.action) {
      const idx = triggers.value.findIndex(
        (t) =>
          t.resource_type === data.trigger.resource_type &&
          t.action === data.trigger.action,
      );
      if (idx >= 0) selectedTriggerIdx.value = idx;
    }
  } catch {
    // corrupt entry — drop it silently
  }
}

function saveTestStateToStorage() {
  if (!_testStorageHydrated) return;
  try {
    localStorage.setItem(
      testStorageKey.value,
      JSON.stringify({
        payload: testPayloadText.value,
        trigger: selectedTrigger.value,
      }),
    );
  } catch {
    // quota / disabled storage — fail silently
  }
}

onMounted(() => {
  // In add mode triggers are seeded synchronously, so we can hydrate now.
  // In edit mode we have to wait for the API call to populate them.
  if (loaded.value) {
    loadTestStateFromStorage();
    _testStorageHydrated = true;
    return;
  }
  const stop = watch(loaded, (isLoaded) => {
    if (!isLoaded) return;
    loadTestStateFromStorage();
    _testStorageHydrated = true;
    stop();
  });
});

watch(
  [testPayloadText, selectedTriggerIdx, triggers, testStorageKey],
  saveTestStateToStorage,
  { deep: true },
);

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
    uuid: "9aa1b6f0-1a55-4e7f-b40f-2bf5b4c83c12",
    event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    object_uuid: null,
    type: "ip-src",
    category: "Network activity",
    value: "8.8.8.8",
    to_ids: true,
    distribution: 5,
    comment: "C2 server",
    timestamp: 1714579200,
    tags: [{ name: "tlp:amber", colour: "#ffc107" }],
  },
  object: {
    uuid: "0b53a3a4-cf2a-4bb7-9210-29f0aebf8c10",
    event_uuid: "5fbf7e2a-3a18-4f04-9e3a-1c1f0a9d3e10",
    name: "file",
    template_uuid: "688c46fb-5edb-40a3-8273-1af7923e2215",
    template_version: 24,
    description: "Suspicious dropper",
    meta_category: "file",
    distribution: 5,
    timestamp: 1714579200,
    attributes: [
      {
        uuid: "f3a91d29-3711-4d8b-83a5-6b4f9d1f2a02",
        type: "filename",
        value: "invoice.exe",
      },
      {
        uuid: "21cf6a5b-b6a0-4632-8db8-21a4c3a3d9e3",
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
    target_attribute_value: "8.8.8.8",
  },
  sighting: {
    type: 0,
    value: "8.8.8.8",
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
            <small class="text-muted font-monospace">python</small>
            <div class="d-flex align-items-center gap-2">
              <button
                type="button"
                class="btn btn-outline-secondary btn-sm"
                data-bs-toggle="modal"
                data-bs-target="#ctxDocsModal"
                title="Reference for ctx (the SDK passed to handle)"
              >
                <FontAwesomeIcon :icon="faBook" class="me-1" />
                reference
              </button>
            </div>
          </div>
          <div class="card-body p-0">
            <VueMonacoEditor
              v-model:value="script.source"
              language="python"
              :theme="monacoTheme"
              :options="monacoOptions"
              :height="`1000px`"
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
          <div class="card-body d-flex flex-column" style="min-height: 1000px">
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
              class="p-2 small mb-0 flex-grow-1 reactor-log"
              :class="
                monacoTheme === 'vs-dark'
                  ? 'reactor-log-dark'
                  : 'reactor-log-light'
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

    <div
      class="modal fade"
      id="ctxDocsModal"
      tabindex="-1"
      aria-labelledby="ctxDocsModalLabel"
      aria-hidden="true"
    >
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="ctxDocsModalLabel">
              <FontAwesomeIcon :icon="faBook" class="me-2" />
              Reactor Scripts reference
            </h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body small p-0">
            <ul class="nav nav-tabs px-3 pt-2" role="tablist">
              <li class="nav-item" role="presentation">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: ctxModalTab === 'docs' }"
                  @click="ctxModalTab = 'docs'"
                >
                  Docs
                </button>
              </li>
              <li class="nav-item" role="presentation">
                <button
                  type="button"
                  class="nav-link"
                  :class="{ active: ctxModalTab === 'library' }"
                  @click="ctxModalTab = 'library'"
                >
                  Library
                </button>
              </li>
            </ul>

            <div v-show="ctxModalTab === 'docs'" class="p-3">
              <p class="text-muted">
                Your script must define a <code>handle</code> function (or
                whatever you set as <em>Entrypoint</em>). It is invoked once per
                matching trigger event.
              </p>

              <h6 class="mt-3">handle(ctx, payload, trigger)</h6>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Type</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>ctx</code></td>
                    <td><code>ReactorContext</code></td>
                    <td>
                      SDK for reads, writes, and logging. Writes are
                      quota-counted (capped by the script's
                      <code>max_writes</code>) and recorded in the audit log.
                      See the methods listed below.
                    </td>
                  </tr>
                  <tr>
                    <td><code>payload</code></td>
                    <td><code>dict</code></td>
                    <td>
                      The resource that fired the trigger. Shape depends on the
                      trigger's <code>resource_type</code>:
                      <ul class="mb-0">
                        <li>
                          <code>event</code> — event document plus
                          <code>event_uuid</code>.
                        </li>
                        <li>
                          <code>attribute</code> — attribute document plus
                          <code>uuid</code>, <code>object_uuid</code>,
                          <code>event_uuid</code>.
                        </li>
                        <li>
                          <code>object</code> — object document plus
                          <code>uuid</code> and <code>event_uuid</code>.
                        </li>
                        <li>
                          <code>correlation</code> —
                          <code
                            >{source_attribute_uuid, source_event_uuid,
                            target_event_uuid, target_attribute_uuid,
                            target_attribute_type, target_attribute_value}</code
                          >.
                        </li>
                        <li>
                          <code>sighting</code> —
                          <code>{type, value, organisation, timestamp}</code>.
                        </li>
                      </ul>
                      Use the <em>Load sample</em> dropdown in the test sandbox
                      to see a full example for each type.
                    </td>
                  </tr>
                  <tr>
                    <td><code>trigger</code></td>
                    <td><code>dict</code></td>
                    <td>
                      <code>{"resource_type": str, "action": str}</code>
                      — identifies which configured trigger fired the run.
                      Useful when one script is wired to multiple triggers and
                      needs to branch on them. Older 2-arg handlers (<code
                        >def handle(ctx, payload):</code
                      >) are still supported for backward compatibility.
                    </td>
                  </tr>
                </tbody>
              </table>

              <h6 class="mt-3">ctx — Properties</h6>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Returns</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>ctx.run_id</code></td>
                    <td><code>int</code></td>
                    <td>ID of the current run row.</td>
                  </tr>
                  <tr>
                    <td><code>ctx.script_id</code></td>
                    <td><code>int</code></td>
                    <td>ID of this reactor script.</td>
                  </tr>
                </tbody>
              </table>

              <h6 class="mt-3">ctx — Reads</h6>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Returns</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <code>ctx.get_event(event_uuid: str)</code>
                    </td>
                    <td>
                      <code>dict | None</code> — the event document, or
                      <code>None</code> if not found.
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <code>ctx.get_attribute(attribute_uuid: str)</code>
                    </td>
                    <td><code>dict | None</code></td>
                  </tr>
                  <tr>
                    <td>
                      <code>ctx.get_object(object_uuid: str)</code>
                    </td>
                    <td><code>dict | None</code></td>
                  </tr>
                </tbody>
              </table>

              <h6 class="mt-3">ctx — Writes</h6>
              <p class="text-muted mb-2">
                Each write counts against the script's
                <code>max_writes</code> quota. Exceeding the quota raises
                <code>ReactorWriteQuotaExceeded</code>.
              </p>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <code
                        >ctx.add_attribute(event_uuid, type, value,
                        category="External analysis", comment=None,
                        to_ids=None)</code
                      >
                    </td>
                    <td>
                      Create an attribute on an event. Returns the new attribute
                      as a dict.
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <code>ctx.tag_event(event_uuid, tag_name)</code>
                    </td>
                    <td>Attach an existing tag (by name) to an event.</td>
                  </tr>
                  <tr>
                    <td>
                      <code>ctx.tag_attribute(attribute_uuid, tag_name)</code>
                    </td>
                    <td>Attach an existing tag (by name) to an attribute.</td>
                  </tr>
                </tbody>
              </table>

              <h6 class="mt-3">ctx — Enrichment</h6>
              <p class="text-muted mb-2">
                Enrichments call MISP expansion modules. They count against
                <code>max_writes</code> because each call hits an external
                service with its own quotas. The module must be enabled in admin
                settings.
              </p>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <code>ctx.enrich(value, type, module, config=None)</code>
                    </td>
                    <td>
                      Run an expansion module against an indicator. Pass the
                      canonical module name (e.g.
                      <code>"mmdb_lookup"</code>, <code>"whois"</code>,
                      <code>"virustotal"</code>). Returns the module's raw
                      response dict.
                    </td>
                  </tr>
                  <tr>
                    <td>
                      <code>ctx.list_modules(enabled_only=True)</code>
                    </td>
                    <td>
                      Return a list of available modules with their
                      <code>name</code>, <code>type</code>,
                      <code>enabled</code>, supported <code>input</code>/<code
                        >output</code
                      >
                      types and description. Read-only; does not count against
                      the quota.
                    </td>
                  </tr>
                </tbody>
              </table>

              <h6 class="mt-3">ctx — Logging</h6>
              <table class="table table-sm">
                <thead>
                  <tr>
                    <th>Method</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><code>ctx.log(*args)</code></td>
                    <td>
                      Like <code>print</code> — joins args with spaces and
                      writes to both the run log and the worker log.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-show="ctxModalTab === 'library'" class="row g-0">
              <div class="col-md-4 border-end">
                <div class="p-3">
                  <h6 class="mb-2">
                    <FontAwesomeIcon :icon="faBook" class="me-1" />
                    Library
                  </h6>
                  <div
                    class="accordion accordion-flush"
                    id="ctxLibraryAccordion"
                  >
                    <div
                      v-for="(items, category) in EXAMPLE_LIBRARY"
                      :key="category"
                      class="accordion-item"
                    >
                      <h2 class="accordion-header">
                        <button
                          class="accordion-button collapsed py-2"
                          type="button"
                          data-bs-toggle="collapse"
                          :data-bs-target="`#ctxLib-${category}`"
                          aria-expanded="false"
                        >
                          {{ category }}
                          <span class="badge bg-secondary ms-2">
                            {{ items.length }}
                          </span>
                        </button>
                      </h2>
                      <div
                        :id="`ctxLib-${category}`"
                        class="accordion-collapse collapse"
                        data-bs-parent="#ctxLibraryAccordion"
                      >
                        <div class="accordion-body p-0">
                          <ul class="list-group list-group-flush">
                            <li
                              v-for="example in items"
                              :key="example.title"
                              class="list-group-item list-group-item-action py-2 small"
                              :class="{
                                active:
                                  selectedExample &&
                                  selectedExample.title === example.title,
                              }"
                              role="button"
                              @click="selectExample(example)"
                            >
                              {{ example.title }}
                            </li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div class="col-md-8">
                <div class="p-3">
                  <div
                    v-if="selectedExample"
                    class="d-flex justify-content-between align-items-center mb-2"
                  >
                    <h6 class="mb-0">{{ selectedExample.title }}</h6>
                    <button
                      type="button"
                      class="btn btn-outline-primary btn-sm"
                      @click="useExampleAsSource"
                      title="Replace the editor source with this example"
                    >
                      Use as starting point
                    </button>
                  </div>
                  <VueMonacoEditor
                    v-if="selectedExample"
                    :value="selectedExample.source"
                    language="python"
                    :theme="monacoTheme"
                    :options="ctxExampleOptions"
                    :height="`360px`"
                  />
                  <p v-else class="text-muted">
                    Select an example from the library on the left.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button
              type="button"
              class="btn btn-secondary"
              data-bs-dismiss="modal"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reactor-log {
  overflow: auto;
  min-height: 180px;
  white-space: pre-wrap;
}
.reactor-log-dark {
  background: #1e1e1e;
  color: #d4d4d4;
}
.reactor-log-light {
  background: #f6f8fa;
  color: #24292f;
}
</style>
