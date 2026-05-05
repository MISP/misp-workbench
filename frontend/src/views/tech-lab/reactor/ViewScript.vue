<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink, useRouter } from "vue-router";
import { useReactorStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { authHelper } from "@/helpers";
import { VueMonacoEditor } from "@guolao/vue-monaco-editor";
import {
  faHourglassHalf,
  faPen,
  faRefresh,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const props = defineProps({ id: { type: [String, Number], required: true } });

const monacoOptions = {
  fontSize: 13,
  readOnly: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: "on",
  renderLineHighlight: "none",
};

function detectMonacoTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "vs-dark"
    : "vs";
}
const monacoTheme = ref(detectMonacoTheme());
let themeObserver = null;

const router = useRouter();
const reactorStore = useReactorStore();
const toastsStore = useToastsStore();
const authStore = useAuthStore();
const { script, runs, status } = storeToRefs(reactorStore);
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() =>
  authHelper.hasScope(scopes.value, "reactor:update"),
);
const canDelete = computed(() =>
  authHelper.hasScope(scopes.value, "reactor:delete"),
);
const source = ref("");
const runLogs = reactive({});
const cardId = Math.random().toString(36).substring(2, 8);
const activeRunFilter = ref("ALL"); // ALL | success | failed

const runItems = computed(() => runs.value?.items ?? []);

const runSuccessCount = computed(
  () => runItems.value.filter((r) => r.status === "success").length,
);
const runFailedCount = computed(
  () =>
    runItems.value.filter(
      (r) => r.status === "failed" || r.status === "timed_out",
    ).length,
);

const filteredRuns = computed(() => {
  if (activeRunFilter.value === "success") {
    return runItems.value.filter((r) => r.status === "success");
  }
  if (activeRunFilter.value === "failed") {
    return runItems.value.filter(
      (r) => r.status === "failed" || r.status === "timed_out",
    );
  }
  return runItems.value;
});

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
  await reactorStore.getById(props.id);
  const sourceResp = await reactorStore.getSource(props.id);
  source.value = sourceResp.source;
  await reactorStore.getRuns(props.id);
});

onBeforeUnmount(() => {
  themeObserver?.disconnect();
  themeObserver = null;
});

async function refreshRuns() {
  await reactorStore.getRuns(props.id, { page: 1 });
}

async function loadMoreRuns() {
  await reactorStore.loadMoreRuns(props.id);
}

const hasMoreRuns = computed(() => {
  if (!runs.value) return false;
  const loaded = runs.value.items?.length ?? 0;
  return loaded < (runs.value.total ?? 0);
});

async function ensureRunLog(run) {
  if (runLogs[run.id] !== undefined) return;
  runLogs[run.id] = null;
  try {
    const resp = await reactorStore.getRunLog(run.id);
    runLogs[run.id] = resp.log ?? "";
  } catch (err) {
    runLogs[run.id] = `(failed to load log: ${err?.message || err})`;
  }
}

function formatTimestamp(ts) {
  return ts ? dayjs.utc(ts).local().format("YYYY-MM-DD HH:mm:ss") : "—";
}

function runPayload(run) {
  const t = run.triggered_by || {};
  return t.payload !== undefined ? t.payload : t;
}

function runStatusBadge(s) {
  if (s === "success") return "bg-success";
  if (s === "failed" || s === "timed_out") return "bg-danger";
  return "bg-secondary";
}

const SLOW_RUN_MS = 100;

function runDurationMs(run) {
  if (!run.started_at) return null;
  const end = run.finished_at ? dayjs.utc(run.finished_at) : dayjs.utc();
  const ms = end.diff(dayjs.utc(run.started_at));
  return ms >= 0 ? ms : null;
}

function formatDuration(run) {
  const ms = runDurationMs(run);
  if (ms === null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(2)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = Math.floor((ms % 60_000) / 1000);
  return `${minutes}m ${seconds}s`;
}

function isSlowRun(run) {
  const ms = runDurationMs(run);
  return ms !== null && ms > SLOW_RUN_MS;
}

async function deleteScript() {
  if (!confirm(`Delete reactor script "${script.value.name}"?`)) return;
  await reactorStore.delete(props.id);
  toastsStore.push("Reactor script deleted.", "success");
  router.push("/tech-lab/reactor");
}
</script>

<template>
  <Spinner v-if="status.loading && !script" />
  <div v-else-if="script">
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <h4 class="mb-0">{{ script.name }}</h4>
        <small class="text-muted">{{ script.description || "—" }}</small>
      </div>
      <div class="d-flex gap-2">
        <RouterLink
          v-if="canUpdate"
          :to="`/tech-lab/reactor/update/${script.id}`"
          class="btn btn-outline-primary btn-sm"
        >
          <FontAwesomeIcon :icon="faPen" />
        </RouterLink>
        <button
          v-if="canDelete"
          class="btn btn-outline-danger btn-sm"
          @click="deleteScript"
        >
          <FontAwesomeIcon :icon="faTrash" />
        </button>
      </div>
    </div>

    <div class="row mb-4">
      <div class="col-12">
        <dl class="row mb-0 small">
          <dt class="col-sm-2">Status</dt>
          <dd class="col-sm-10">
            <span
              class="badge"
              :class="
                script.status === 'active' ? 'bg-success' : 'bg-secondary'
              "
              >{{ script.status }}</span
            >
          </dd>
          <dt class="col-sm-2">Triggers</dt>
          <dd class="col-sm-10 font-monospace">
            <div v-for="(t, i) in script.triggers" :key="i">
              {{ t.resource_type }}.{{ t.action
              }}<span v-if="t.filters && Object.keys(t.filters).length">
                ({{ JSON.stringify(t.filters) }})</span
              >
            </div>
          </dd>
          <dt class="col-sm-2">Entrypoint</dt>
          <dd class="col-sm-10 font-monospace">{{ script.entrypoint }}</dd>
          <dt class="col-sm-2">Timeout</dt>
          <dd class="col-sm-10">{{ script.timeout_seconds }}s</dd>
          <dt class="col-sm-2">Max writes</dt>
          <dd class="col-sm-10">{{ script.max_writes }}</dd>
          <dt class="col-sm-2">Last run</dt>
          <dd class="col-sm-10">
            <template v-if="script.last_run_at">
              {{ dayjs.utc(script.last_run_at).local().fromNow() }}
              ({{ script.last_run_status }})
            </template>
            <template v-else>never</template>
          </dd>
          <dt class="col-sm-2">SHA-256</dt>
          <dd class="col-sm-10 font-monospace small text-truncate">
            {{ script.source_sha256 }}
          </dd>
        </dl>
      </div>
    </div>

    <div class="card mb-4">
      <div
        class="card-header d-flex justify-content-between align-items-center"
      >
        <small class="text-muted font-monospace">python</small>
      </div>
      <div class="card-body p-0">
        <VueMonacoEditor
          :value="source"
          language="python"
          :theme="monacoTheme"
          :options="monacoOptions"
          :height="`1000px`"
        />
      </div>
    </div>

    <div class="card">
      <div
        class="card-header d-flex align-items-center justify-content-between"
      >
        <div class="d-flex align-items-center flex-wrap gap-2">
          <span>Run history</span>
          <span
            class="badge bg-info"
            :class="
              activeRunFilter === 'ALL'
                ? 'shadow border border-warning-subtle'
                : 'fw-light'
            "
            role="button"
            @click="activeRunFilter = 'ALL'"
          >
            total: {{ runItems.length }}
          </span>
          <span
            v-if="runSuccessCount > 0"
            class="badge bg-success"
            :class="
              activeRunFilter === 'success'
                ? 'shadow border border-warning-subtle'
                : 'fw-light'
            "
            role="button"
            @click="activeRunFilter = 'success'"
          >
            succeeded: {{ runSuccessCount }}
          </span>
          <span
            v-if="runFailedCount > 0"
            class="badge bg-danger"
            :class="
              activeRunFilter === 'failed'
                ? 'shadow border border-warning-subtle'
                : 'fw-light'
            "
            role="button"
            @click="activeRunFilter = 'failed'"
          >
            failed: {{ runFailedCount }}
          </span>
        </div>
        <button class="btn btn-outline-secondary btn-sm" @click="refreshRuns">
          <FontAwesomeIcon :icon="faRefresh" />
        </button>
      </div>
      <div class="card-body p-0">
        <div
          v-if="filteredRuns.length > 0"
          class="accordion accordion-flush"
          :id="'runAccordion-' + cardId"
        >
          <div v-for="run in filteredRuns" :key="run.id" class="accordion-item">
            <h2
              class="accordion-header"
              :id="'run-heading-' + cardId + '-' + run.id"
            >
              <button
                class="accordion-button collapsed"
                type="button"
                data-bs-toggle="collapse"
                :data-bs-target="'#run-collapse-' + cardId + '-' + run.id"
                aria-expanded="false"
                :aria-controls="'run-collapse-' + cardId + '-' + run.id"
                @click="ensureRunLog(run)"
              >
                <div
                  class="d-flex flex-wrap align-items-center gap-3 w-100 small"
                >
                  <span class="text-muted font-monospace">#{{ run.id }}</span>
                  <span class="text-muted">{{
                    formatTimestamp(run.started_at)
                  }}</span>
                  <span class="badge" :class="runStatusBadge(run.status)">
                    {{ run.status }}
                  </span>
                  <span :class="isSlowRun(run) ? 'text-warning' : 'text-muted'">
                    {{ formatDuration(run) }}
                    <FontAwesomeIcon
                      v-if="isSlowRun(run)"
                      :icon="faHourglassHalf"
                      class="ms-1"
                      title="slow run (>100ms)"
                    />
                  </span>
                  <span class="text-muted">writes: {{ run.writes_count }}</span>
                  <span class="font-monospace text-muted">
                    {{ run.triggered_by?.resource_type }}.{{
                      run.triggered_by?.action
                    }}
                  </span>
                </div>
              </button>
            </h2>
            <div
              :id="'run-collapse-' + cardId + '-' + run.id"
              class="accordion-collapse collapse"
              :aria-labelledby="'run-heading-' + cardId + '-' + run.id"
              :data-bs-parent="'#runAccordion-' + cardId"
            >
              <div class="accordion-body small">
                <ul class="list-group list-group-flush mb-3">
                  <li class="list-group-item">
                    <strong>Run ID:</strong> {{ run.id }}
                  </li>
                  <li class="list-group-item">
                    <strong>Status:</strong>
                    <span
                      class="badge ms-1"
                      :class="runStatusBadge(run.status)"
                    >
                      {{ run.status }}
                    </span>
                  </li>
                  <li class="list-group-item">
                    <strong>Created:</strong>
                    {{ formatTimestamp(run.created_at) }}
                  </li>
                  <li class="list-group-item">
                    <strong>Started:</strong>
                    {{ formatTimestamp(run.started_at) }}
                  </li>
                  <li class="list-group-item">
                    <strong>Finished:</strong>
                    {{ formatTimestamp(run.finished_at) }}
                  </li>
                  <li class="list-group-item">
                    <strong>Runtime:</strong>
                    <span :class="isSlowRun(run) ? 'text-warning' : ''">
                      {{ formatDuration(run) }}
                    </span>
                    <FontAwesomeIcon
                      v-if="isSlowRun(run)"
                      :icon="faHourglassHalf"
                      class="ms-1 text-warning"
                      title="slow run (>100ms)"
                    />
                  </li>
                  <li class="list-group-item">
                    <strong>Writes:</strong> {{ run.writes_count }}
                  </li>
                  <li class="list-group-item">
                    <strong>Trigger:</strong>
                    <span class="font-monospace ms-1">
                      {{ run.triggered_by?.resource_type }}.{{
                        run.triggered_by?.action
                      }}
                    </span>
                  </li>
                  <li v-if="run.celery_task_id" class="list-group-item">
                    <strong>Celery task:</strong>
                    <span class="font-monospace ms-1">{{
                      run.celery_task_id
                    }}</span>
                  </li>
                  <li v-if="run.error" class="list-group-item text-danger">
                    <strong>Error:</strong>
                    <pre class="mb-0 mt-1 small">{{ run.error }}</pre>
                  </li>
                  <li class="list-group-item">
                    <strong>Payload:</strong>
                    <pre class="mb-0 mt-1 font-monospace small">{{
                      JSON.stringify(runPayload(run), null, 2)
                    }}</pre>
                  </li>
                </ul>
                <div>
                  <h6 class="small text-muted mb-1">Log</h6>
                  <pre
                    v-if="
                      runLogs[run.id] !== undefined && runLogs[run.id] !== null
                    "
                    class="p-2 small mb-0"
                    style="max-height: 300px; overflow: auto"
                    >{{ runLogs[run.id] || "(empty)" }}</pre
                  >
                  <Spinner v-else />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="p-3 text-muted small">
          {{
            runItems.length === 0
              ? "No runs yet."
              : "No runs match this filter."
          }}
        </div>
      </div>
      <div
        v-if="runs && runs.items && runs.items.length > 0"
        class="card-footer d-flex justify-content-between align-items-center"
      >
        <small class="text-muted">
          Showing {{ runs.items.length }} of
          {{ runs.total ?? runs.items.length }}
        </small>
        <button
          v-if="hasMoreRuns"
          type="button"
          class="btn btn-sm btn-outline-primary"
          :disabled="status.loadingMoreRuns"
          @click="loadMoreRuns"
        >
          {{ status.loadingMoreRuns ? "Loading…" : "Load more" }}
        </button>
      </div>
    </div>
  </div>
</template>
