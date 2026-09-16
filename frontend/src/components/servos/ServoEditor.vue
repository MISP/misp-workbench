<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from "vue";
import { router } from "@/router";
import { useServosStore, useToastsStore } from "@/stores";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faPlay,
  faTriangleExclamation,
  faTrashCan,
  faWandMagicSparkles,
} from "@fortawesome/free-solid-svg-icons";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps({
  mode: {
    type: String,
    default: "add",
    validator: (v) => ["add", "edit"].includes(v),
  },
  servoId: { type: [String, Number], default: null },
});

const servosStore = useServosStore();
const toastsStore = useToastsStore();

const DEFAULT_SAMPLE = { type: "ip-src", value: "1.2.3.4" };

const servo = reactive({
  slug: "",
  name: "",
  description: "",
  enabled: true,
});

const processorsJson = ref("[\n  \n]");
const sampleJson = ref(JSON.stringify(DEFAULT_SAMPLE, null, 2));
const templates = ref([]);
const loaded = ref(props.mode === "add");
const saving = ref(false);
// A servo is only allowed to go live once OpenSearch has accepted it, so the
// dry run is a gate rather than a convenience.
const simulation = ref(null);

const monacoOptions = {
  fontSize: 13,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 2,
  insertSpaces: true,
  wordWrap: "on",
};

function detectMonacoTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "vs-dark"
    : "vs";
}

const monacoTheme = ref(detectMonacoTheme());
let themeObserver = null;

const parsedProcessors = computed(() => {
  try {
    const parsed = JSON.parse(processorsJson.value);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
});

const parsedSample = computed(() => {
  try {
    return JSON.parse(sampleJson.value);
  } catch {
    return null;
  }
});

// Mirrors chain.drops_documents on the API side: `foreach` and `on_failure`
// can hide a drop that a top-level scan would miss.
function containsDrop(processors) {
  for (const processor of processors ?? []) {
    if (typeof processor !== "object" || processor === null) continue;
    for (const [kind, config] of Object.entries(processor)) {
      if (kind === "drop") return true;
      if (typeof config !== "object" || config === null) continue;
      if (config.processor && containsDrop([config.processor])) return true;
      for (const nested of ["on_failure", "processors"]) {
        if (Array.isArray(config[nested]) && containsDrop(config[nested]))
          return true;
      }
    }
  }
  return false;
}

const dropsDocuments = computed(() => containsDrop(parsedProcessors.value));

const jsonError = computed(() => {
  if (parsedProcessors.value === null)
    return "Processors must be a JSON array of processor objects.";
  if (parsedProcessors.value.length === 0) return "Add at least one processor.";
  const bad = parsedProcessors.value.findIndex(
    (p) => typeof p !== "object" || p === null || Object.keys(p).length !== 1,
  );
  if (bad !== -1)
    return `Processor ${bad} must be an object with exactly one key naming the processor type.`;
  return null;
});

const canSave = computed(
  () =>
    !jsonError.value &&
    servo.slug &&
    servo.name &&
    simulation.value?.ok === true,
);

onMounted(async () => {
  themeObserver = new MutationObserver((mutations) => {
    if (mutations.some((m) => m.attributeName === "data-bs-theme")) {
      monacoTheme.value = detectMonacoTheme();
    }
  });
  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-bs-theme"],
  });

  // A failed template fetch must not take the editor down with it. Without
  // this the rejection aborts the rest of onMounted, so in edit mode the servo
  // is never loaded and the page sits on a spinner for ever — and in add mode
  // the picker just silently vanishes with nothing to explain why.
  try {
    templates.value = (await servosStore.getTemplates()) ?? [];
  } catch (err) {
    templates.value = [];
    toastsStore.push(
      err || "Could not load servo templates; you can still write your own.",
      "warning",
    );
  }

  if (props.mode === "edit" && props.servoId) {
    const existing = await servosStore.getById(props.servoId);
    servo.slug = existing.slug;
    servo.name = existing.name;
    servo.description = existing.description ?? "";
    servo.enabled = existing.enabled;
    processorsJson.value = JSON.stringify(existing.processors, null, 2);
    loaded.value = true;
  }
});

onBeforeUnmount(() => {
  themeObserver?.disconnect();
  themeObserver = null;
});

function applyTemplate(template) {
  servo.slug = servo.slug || template.slug;
  servo.name = servo.name || template.name;
  servo.description = servo.description || template.description;
  processorsJson.value = JSON.stringify(template.processors, null, 2);
  if (template.sample_doc && Object.keys(template.sample_doc).length > 0) {
    sampleJson.value = JSON.stringify(template.sample_doc, null, 2);
  }
  simulation.value = null;
}

async function dryRun() {
  if (jsonError.value) return;
  simulation.value = null;
  try {
    simulation.value = await servosStore.simulate({
      processors: parsedProcessors.value,
      docs: parsedSample.value ? [parsedSample.value] : [DEFAULT_SAMPLE],
    });
  } catch (err) {
    toastsStore.push(err || "Dry run failed.", "danger");
  }
}

async function save() {
  saving.value = true;
  const payload = {
    name: servo.name,
    description: servo.description || null,
    processors: parsedProcessors.value,
    enabled: servo.enabled,
  };
  try {
    if (props.mode === "edit") {
      await servosStore.update(props.servoId, payload);
      toastsStore.push(`Servo "${servo.name}" updated.`, "success");
    } else {
      await servosStore.create({ ...payload, slug: servo.slug });
      toastsStore.push(`Servo "${servo.name}" created.`, "success");
    }
    router.push("/tech-lab/servos");
  } catch (err) {
    toastsStore.push(err || "Failed to save servo.", "danger");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Spinner v-if="!loaded" />
  <div v-else>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="mb-0">
          {{ mode === "edit" ? "Edit" : "New" }} Transformation Servo
        </h4>
        <small class="text-muted"
          >Tech Lab — an OpenSearch ingest pipeline that runs on every attribute
          indexed into <code>misp-attributes</code>.</small
        >
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-outline-success btn-sm" @click="dryRun">
          <FontAwesomeIcon :icon="faPlay" class="me-1" />
          dry run
        </button>
        <button
          class="btn btn-primary btn-sm"
          :disabled="!canSave || saving"
          @click="save"
        >
          {{ saving ? "saving…" : "save" }}
        </button>
      </div>
    </div>

    <div class="alert alert-warning d-flex gap-2 align-items-start py-2">
      <FontAwesomeIcon :icon="faTriangleExclamation" class="mt-1" />
      <div class="small">
        This is ingestion logic. An enabled servo runs on
        <strong>every</strong> attribute written to
        <code>misp-attributes</code>, and only affects documents indexed
        <strong>after</strong> it is enabled — existing attributes are
        untouched. A servo that throws is recorded in
        <code>expanded.servo_errors</code> on the document rather than failing
        the write, so a mistake here degrades enrichment, it does not stop
        ingestion.
      </div>
    </div>

    <div
      v-if="dropsDocuments"
      class="alert alert-danger d-flex gap-2 align-items-start py-2"
    >
      <FontAwesomeIcon :icon="faTrashCan" class="mt-1" />
      <div class="small">
        <strong>This servo discards attributes.</strong> A
        <code>drop</code> processor stops the attribute reaching
        <code>misp-attributes</code> entirely — it will not be searchable,
        correlated, hunted or exported, and none of it is recoverable without
        re-importing the source. Creating such an attribute through the API is
        rejected with a clear error rather than silently reported as created,
        but anything arriving through a feed is simply counted as failed.
      </div>
    </div>

    <div class="row g-3">
      <div class="col-lg-7">
        <div class="card mb-3">
          <div class="card-body">
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label small">name</label>
                <input
                  v-model="servo.name"
                  class="form-control form-control-sm"
                />
              </div>
              <div class="col-md-6">
                <label class="form-label small">slug</label>
                <input
                  v-model="servo.slug"
                  class="form-control form-control-sm font-monospace"
                  :disabled="mode === 'edit'"
                  placeholder="url_parts"
                />
                <div class="form-text small">
                  Pipeline name:
                  <code>servo_{{ servo.slug || "…" }}</code
                  >. Cannot be changed later, and cannot start with
                  <code>misp-</code>.
                </div>
              </div>
              <div class="col-12">
                <label class="form-label small">description</label>
                <textarea
                  v-model="servo.description"
                  class="form-control form-control-sm"
                  rows="2"
                ></textarea>
              </div>
              <div class="col-12">
                <div class="form-check form-switch">
                  <input
                    id="servo-enabled"
                    v-model="servo.enabled"
                    class="form-check-input"
                    type="checkbox"
                  />
                  <label class="form-check-label small" for="servo-enabled"
                    >enabled — add to the live ingestion chain</label
                  >
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div
            class="card-header d-flex justify-content-between align-items-center"
          >
            <span>Processors</span>
            <div v-if="templates.length" class="dropdown">
              <button
                class="btn btn-outline-secondary btn-sm dropdown-toggle"
                data-bs-toggle="dropdown"
              >
                <FontAwesomeIcon :icon="faWandMagicSparkles" class="me-1" />
                start from a template
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li v-for="template in templates" :key="template.slug">
                  <button
                    class="dropdown-item"
                    @click="applyTemplate(template)"
                  >
                    <div class="fw-semibold">{{ template.name }}</div>
                    <div class="text-muted small">{{ template.summary }}</div>
                  </button>
                </li>
              </ul>
            </div>
          </div>
          <div class="card-body p-0">
            <VueMonacoEditor
              v-model:value="processorsJson"
              language="json"
              :theme="monacoTheme"
              :options="monacoOptions"
              height="480px"
            />
          </div>
          <div v-if="jsonError" class="card-footer text-danger small">
            {{ jsonError }}
          </div>
        </div>
      </div>

      <div class="col-lg-5">
        <div class="card h-100">
          <div class="card-header">Dry run</div>
          <div class="card-body">
            <p class="text-muted small">
              Runs the processors through OpenSearch's
              <code>_simulate</code> endpoint. Nothing is written. A servo can
              only be saved once a dry run succeeds.
            </p>
            <label class="form-label small">sample attribute document</label>
            <div class="border rounded mb-3">
              <VueMonacoEditor
                v-model:value="sampleJson"
                language="json"
                :theme="monacoTheme"
                :options="monacoOptions"
                height="160px"
              />
            </div>

            <Spinner v-if="servosStore.status.simulating" />
            <template v-else-if="simulation">
              <div
                v-if="!simulation.ok"
                class="alert alert-danger small mb-0"
                style="white-space: pre-wrap"
              >
                {{ simulation.error }}
              </div>
              <template v-else>
                <div class="alert alert-success small py-1">
                  OpenSearch accepted these processors.
                </div>
                <label class="form-label small">resulting document</label>
                <pre
                  class="bg-body-tertiary border rounded p-2 small mb-0 overflow-auto"
                  style="max-height: 20rem"
                  >{{ JSON.stringify(simulation.docs, null, 2) }}</pre
                >
              </template>
            </template>
            <p v-else class="text-muted small fst-italic mb-0">
              No dry run yet.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
