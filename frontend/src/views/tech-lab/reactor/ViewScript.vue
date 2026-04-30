<script setup>
import { ref, onMounted, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink, useRouter } from "vue-router";
import { useReactorStore, useAuthStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { authHelper } from "@/helpers";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const props = defineProps({ id: { type: [String, Number], required: true } });

const router = useRouter();
const reactorStore = useReactorStore();
const toastsStore = useToastsStore();
const authStore = useAuthStore();
const { script, runs, status } = storeToRefs(reactorStore);
const { scopes } = storeToRefs(authStore);

const canUpdate = computed(() => authHelper.hasScope(scopes.value, "reactor:update"));
const canDelete = computed(() => authHelper.hasScope(scopes.value, "reactor:delete"));
const canRun = computed(() => authHelper.hasScope(scopes.value, "reactor:run"));

const source = ref("");
const testPayload = ref('{}');
const testResult = ref(null);
const testLog = ref(null);
const selectedRunId = ref(null);
const selectedRunLog = ref(null);

onMounted(async () => {
  await reactorStore.getById(props.id);
  const sourceResp = await reactorStore.getSource(props.id);
  source.value = sourceResp.source;
  await reactorStore.getRuns(props.id);
});

async function refreshRuns() {
  await reactorStore.getRuns(props.id);
}

async function runTest() {
  testResult.value = null;
  testLog.value = null;
  let parsed;
  try {
    parsed = JSON.parse(testPayload.value || "{}");
  } catch (e) {
    toastsStore.push(`Invalid JSON: ${e.message}`, "danger");
    return;
  }
  try {
    const run = await reactorStore.test(props.id, parsed);
    testResult.value = run;
    const log = await reactorStore.getRunLog(run.id);
    testLog.value = log.log;
    await refreshRuns();
  } catch (err) {
    toastsStore.push(err?.message || String(err), "danger");
  }
}

async function viewRunLog(run) {
  selectedRunId.value = run.id;
  selectedRunLog.value = null;
  const log = await reactorStore.getRunLog(run.id);
  selectedRunLog.value = log.log;
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
          class="btn btn-outline-secondary btn-sm"
        >
          Edit
        </RouterLink>
        <button
          v-if="canDelete"
          class="btn btn-outline-danger btn-sm"
          @click="deleteScript"
        >
          Delete
        </button>
      </div>
    </div>

    <div class="row mb-4">
      <div class="col-md-6">
        <dl class="row mb-0 small">
          <dt class="col-sm-4">Status</dt>
          <dd class="col-sm-8">
            <span
              class="badge"
              :class="script.status === 'active' ? 'bg-success' : 'bg-secondary'"
              >{{ script.status }}</span
            >
          </dd>
          <dt class="col-sm-4">Triggers</dt>
          <dd class="col-sm-8 font-monospace">
            <div v-for="(t, i) in script.triggers" :key="i">
              {{ t.resource_type }}.{{ t.action
              }}<span v-if="t.filters && Object.keys(t.filters).length">
                ({{ JSON.stringify(t.filters) }})</span>
            </div>
          </dd>
          <dt class="col-sm-4">Entrypoint</dt>
          <dd class="col-sm-8 font-monospace">{{ script.entrypoint }}</dd>
          <dt class="col-sm-4">Timeout</dt>
          <dd class="col-sm-8">{{ script.timeout_seconds }}s</dd>
          <dt class="col-sm-4">Max writes</dt>
          <dd class="col-sm-8">{{ script.max_writes }}</dd>
          <dt class="col-sm-4">Last run</dt>
          <dd class="col-sm-8">
            <template v-if="script.last_run_at">
              {{ dayjs.utc(script.last_run_at).local().fromNow() }}
              ({{ script.last_run_status }})
            </template>
            <template v-else>never</template>
          </dd>
          <dt class="col-sm-4">SHA-256</dt>
          <dd class="col-sm-8 font-monospace small text-truncate">
            {{ script.source_sha256 }}
          </dd>
        </dl>
      </div>
      <div class="col-md-6" v-if="canRun">
        <div class="card">
          <div class="card-header">Test run</div>
          <div class="card-body">
            <label class="form-label small">payload (JSON)</label>
            <textarea
              class="form-control font-monospace small"
              rows="4"
              v-model="testPayload"
            />
            <button
              class="btn btn-primary btn-sm mt-2"
              :disabled="reactorStore.status.testing"
              @click="runTest"
            >
              {{ reactorStore.status.testing ? "Running…" : "Run" }}
            </button>
            <div v-if="testResult" class="mt-3">
              <div class="small">
                Status:
                <span
                  class="badge"
                  :class="
                    testResult.status === 'success' ? 'bg-success' : 'bg-danger'
                  "
                  >{{ testResult.status }}</span
                >
              </div>
              <pre
                class="bg-light p-2 mt-2 small"
                v-if="testLog"
                style="max-height: 200px; overflow: auto"
                >{{ testLog }}</pre
              >
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card mb-4">
      <div class="card-header">Source</div>
      <div class="card-body p-0">
        <pre class="m-0 p-3 font-monospace small" style="white-space: pre-wrap">{{
          source
        }}</pre>
      </div>
    </div>

    <div class="card">
      <div class="card-header d-flex justify-content-between align-items-center">
        <span>Run history</span>
        <button class="btn btn-outline-secondary btn-sm" @click="refreshRuns">
          refresh
        </button>
      </div>
      <div class="card-body p-0">
        <table v-if="runs && runs.items && runs.items.length > 0" class="table table-sm mb-0">
          <thead>
            <tr>
              <th>started</th>
              <th>status</th>
              <th>writes</th>
              <th>trigger</th>
              <th class="text-end"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs.items" :key="run.id">
              <td class="small text-muted">
                {{
                  run.started_at
                    ? dayjs.utc(run.started_at).local().format("YYYY-MM-DD HH:mm:ss")
                    : "—"
                }}
              </td>
              <td>
                <span
                  class="badge"
                  :class="
                    run.status === 'success'
                      ? 'bg-success'
                      : run.status === 'failed' || run.status === 'timed_out'
                      ? 'bg-danger'
                      : 'bg-secondary'
                  "
                  >{{ run.status }}</span
                >
              </td>
              <td class="small">{{ run.writes_count }}</td>
              <td class="small font-monospace">
                {{ run.triggered_by?.resource_type }}.{{ run.triggered_by?.action }}
              </td>
              <td class="text-end">
                <button
                  class="btn btn-outline-secondary btn-sm"
                  @click="viewRunLog(run)"
                >
                  log
                </button>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else class="p-3 text-muted small">No runs yet.</div>
      </div>
    </div>

    <div v-if="selectedRunId" class="mt-3">
      <h6 class="small text-muted">Run #{{ selectedRunId }} log</h6>
      <pre
        class="bg-light p-2 small"
        style="max-height: 300px; overflow: auto"
        v-if="selectedRunLog !== null"
      >{{ selectedRunLog || "(empty)" }}</pre>
      <Spinner v-else />
    </div>
  </div>
</template>
