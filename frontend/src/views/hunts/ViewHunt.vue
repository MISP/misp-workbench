<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useHuntsStore, useTasksStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import ScheduledTaskActions from "@/components/tasks/ScheduledTaskActions.vue";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faArrowLeft, faPen } from "@fortawesome/free-solid-svg-icons";
import { formatSchedule } from "@/helpers";
import { Line } from "vue-chartjs";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
} from "chart.js";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
);

dayjs.extend(utc);
dayjs.extend(relativeTime);

const props = defineProps({ id: { type: String, required: true } });

const huntsStore = useHuntsStore();
const tasksStore = useTasksStore();
const toastsStore = useToastsStore();
const { hunt, status } = storeToRefs(huntsStore);
const { scheduledTasks } = storeToRefs(tasksStore);

const runResult = ref(null);
const runError = ref(null);
const cachedResult = ref(null);
const displayResult = computed(() => runResult.value ?? cachedResult.value);
const resultIsCached = computed(() => !runResult.value && !!cachedResult.value);
const newCount = computed(
  () => displayResult.value?.hits?.filter((h) => h.is_new).length ?? 0,
);

const history = ref([]);
const sparklineData = computed(() => ({
  labels: history.value.map((e) =>
    dayjs.utc(e.run_at).local().format("MMM D HH:mm"),
  ),
  datasets: [
    {
      data: history.value.map((e) => e.match_count),
      borderColor: "#0d6efd",
      backgroundColor: "rgba(13,110,253,0.12)",
      fill: true,
      pointRadius: history.value.length > 20 ? 0 : 3,
      pointHoverRadius: 4,
    },
  ],
}));
const sparklineOptions = ref({
  responsive: true,
  maintainAspectRatio: false,
  animation: false,
  plugins: {
    legend: { display: false },
    tooltip: { mode: "index", intersect: false },
  },
  scales: { x: { display: false }, y: { display: false, beginAtZero: true } },
});

const scheduleInterval = ref("86400");
const scheduleError = ref(null);
const scheduling = ref(false);

huntsStore.getById(props.id);
tasksStore.get_scheduled_tasks();
huntsStore.getResults(props.id).then((r) => {
  if (r) cachedResult.value = r;
});
huntsStore.getHistory(props.id).then((h) => {
  if (h) history.value = h;
});

const huntSchedules = computed(() =>
  scheduledTasks.value.filter((t) => t.kwargs?.hunt_id === parseInt(props.id)),
);

async function saveSchedule() {
  scheduleError.value = null;
  scheduling.value = true;
  const taskData = {
    task_name: "app.worker.tasks.run_hunt",
    params: { kwargs: { hunt_id: parseInt(props.id) } },
    schedule: { type: "interval", every: parseInt(scheduleInterval.value) },
    enabled: true,
  };
  await tasksStore
    .create_scheduled_task(taskData)
    .then(() => {
      toastsStore.push("Hunt scheduled successfully.", "success");
      tasksStore.get_scheduled_tasks();
    })
    .catch((err) => (scheduleError.value = err?.message || String(err)))
    .finally(() => (scheduling.value = false));
}

async function clearHistory() {
  await huntsStore.deleteHistory(props.id);
  history.value = [];
  cachedResult.value = null;
  runResult.value = null;
}

async function runHunt() {
  runResult.value = null;
  runError.value = null;
  await huntsStore
    .run(props.id)
    .then((result) => {
      runResult.value = result;
      if (hunt.value) {
        hunt.value.last_match_count = result.total;
        hunt.value.last_run_at = new Date().toISOString();
      }
      huntsStore.getHistory(props.id).then((h) => {
        if (h) history.value = h;
      });
    })
    .catch((err) => (runError.value = err?.message || String(err)));
}
</script>

<template>
  <Spinner v-if="status.loading && !hunt" />

  <div v-else-if="hunt">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <h4 class="mb-1">{{ hunt.name }}</h4>
        <p v-if="hunt.description" class="text-muted mb-0 small">
          {{ hunt.description }}
        </p>
      </div>
      <div class="d-flex gap-2">
        <RouterLink
          :to="`/hunts/update/${hunt.id}`"
          class="btn btn-outline-primary btn-sm"
        >
          <FontAwesomeIcon :icon="faPen" />
        </RouterLink>
        <RouterLink to="/hunts" class="btn btn-outline-secondary btn-sm">
          <FontAwesomeIcon :icon="faArrowLeft" />
        </RouterLink>
      </div>
    </div>

    <!-- Meta card -->
    <div class="card mb-3">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-4">
            <div class="text-muted small mb-1">Type</div>
            <span class="badge bg-primary">{{ hunt.hunt_type }}</span>
          </div>
          <div v-if="hunt.hunt_type === 'opensearch'" class="col-md-4">
            <div class="text-muted small mb-1">Search index</div>
            <span class="badge bg-secondary">{{ hunt.index_target }}</span>
          </div>
          <div class="col-md-4">
            <div class="text-muted small mb-1">Status</div>
            <span
              class="badge"
              :class="hunt.status === 'active' ? 'bg-success' : 'bg-secondary'"
            >
              {{ hunt.status }}
            </span>
          </div>
          <div class="col-md-4">
            <div class="text-muted small mb-1">Last run</div>
            <span>
              {{
                hunt.last_run_at
                  ? dayjs.utc(hunt.last_run_at).local().fromNow()
                  : "never"
              }}</span
            >
          </div>
        </div>

        <div class="mt-3">
          <div class="text-muted small mb-1">
            {{
              hunt.hunt_type === "rulezet"
                ? "Vuln ID"
                : hunt.hunt_type === "cpe"
                  ? "CPE string"
                  : "Query"
            }}
          </div>
          <code class="d-block p-2 bg-body-secondary rounded">{{
            hunt.query
          }}</code>
        </div>

        <div v-if="history.length > 1" class="mt-3">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <div class="text-muted small">
              Match history ({{ history.length }} runs)
            </div>
            <button class="btn btn-outline-danger btn-sm" @click="clearHistory">
              Clear history
            </button>
          </div>
          <div>
            <Line
              :data="sparklineData"
              :options="sparklineOptions"
              height="80"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Schedule section -->
    <div class="card mb-3">
      <div class="card-body">
        <strong>Schedule</strong>
        <div class="text-muted small mb-3">
          Automatically re-run this hunt at a fixed interval.
        </div>

        <!-- Existing schedules -->
        <template v-if="huntSchedules.length">
          <div
            v-for="task in huntSchedules"
            :key="task.id"
            class="d-flex align-items-center justify-content-between border rounded px-3 py-2 mb-2"
          >
            <div class="small">
              <span
                class="badge me-2"
                :class="task.enabled ? 'bg-success' : 'bg-secondary'"
                >{{ task.enabled ? "enabled" : "disabled" }}</span
              >
              {{ formatSchedule(task.schedule) }}
            </div>
            <ScheduledTaskActions
              :scheduled_task="task"
              @scheduled-task-deleted="tasksStore.get_scheduled_tasks()"
              @scheduled-task-updated="tasksStore.get_scheduled_tasks()"
            />
          </div>
        </template>

        <!-- Add schedule form (shown only when no schedules exist) -->
        <template v-else>
          <div class="d-flex gap-2 align-items-center">
            <select
              class="form-select form-select-sm"
              v-model="scheduleInterval"
              style="width: auto"
            >
              <option value="3600">Hourly</option>
              <option value="86400">Daily</option>
              <option value="604800">Weekly</option>
            </select>
            <button
              class="btn btn-outline-primary btn-sm"
              :disabled="scheduling"
              @click="saveSchedule"
            >
              {{ scheduling ? "Saving…" : "Schedule" }}
            </button>
          </div>
          <div v-if="scheduleError" class="alert alert-danger mt-3 mb-0 small">
            {{ scheduleError }}
          </div>
        </template>
      </div>
    </div>

    <!-- Run section -->
    <div class="card mb-3">
      <div class="card-body">
        <div class="d-flex justify-content-between align-items-center">
          <div>
            <strong>Run hunt</strong>
            <div class="text-muted small">
              Execute the query now and see matching results.
            </div>
          </div>
          <button
            class="btn btn-success"
            :disabled="status.running"
            @click="runHunt"
          >
            {{ status.running ? "Running…" : "Run Now" }}
          </button>
        </div>

        <div v-if="runError" class="alert alert-danger mt-3 mb-0">
          {{ runError }}
        </div>

        <template v-if="displayResult">
          <hr />
          <div class="d-flex justify-content-between align-items-start mb-3">
            <div class="d-flex gap-4">
              <div>
                <span class="fs-3 fw-bold">{{ displayResult.total }}</span>
                <div class="text-muted small">
                  {{
                    hunt.hunt_type === "rulezet"
                      ? "rules found"
                      : hunt.hunt_type === "cpe"
                        ? "Vulnerabilities found"
                        : "total matches"
                  }}
                </div>
              </div>
              <div
                v-if="hunt.hunt_type !== 'rulezet' && hunt.hunt_type !== 'cpe'"
              >
                <span class="fs-3 fw-bold text-primary">{{
                  displayResult.hits.length
                }}</span>
                <div class="text-muted small">shown (max 100)</div>
              </div>
            </div>
            <div class="d-flex flex-column align-items-end gap-1">
              <span v-if="resultIsCached" class="badge bg-secondary">
                last run results
              </span>
              <span v-if="newCount > 0" class="badge bg-warning text-dark">
                {{ newCount }} new since previous run
              </span>
            </div>
          </div>

          <!-- Attribute results -->
          <div
            v-if="
              hunt.hunt_type === 'opensearch' &&
              hunt.index_target === 'attributes' &&
              displayResult.hits.length
            "
            class="table-responsive"
          >
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>type</th>
                  <th>value</th>
                  <th>event</th>
                  <th>category</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(hit, i) in displayResult.hits" :key="i">
                  <td>
                    <code>{{ hit.type }}</code>
                  </td>
                  <td class="text-truncate" style="max-width: 260px">
                    <RouterLink
                      v-if="hit.uuid"
                      :to="`/attributes/${hit.uuid}`"
                      class="text-decoration-none"
                    >
                      {{ hit.value }}
                    </RouterLink>
                    <span v-else>{{ hit.value }}</span>
                    <span
                      v-if="hit.is_new"
                      class="badge bg-warning text-dark ms-2"
                      >new</span
                    >
                  </td>
                  <td>
                    <RouterLink
                      v-if="hit.event_uuid"
                      :to="`/events/${hit.event_uuid}`"
                      class="text-decoration-none small"
                    >
                      {{ hit.event_uuid }}
                    </RouterLink>
                  </td>
                  <td class="text-muted small">{{ hit.category }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Event results -->
          <div
            v-else-if="
              hunt.index_target === 'events' && displayResult.hits.length
            "
            class="table-responsive"
          >
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>uuid</th>
                  <th>info</th>
                  <th>org</th>
                  <th>date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(hit, i) in displayResult.hits" :key="i">
                  <td>
                    <RouterLink
                      v-if="hit.uuid"
                      :to="`/events/${hit.uuid}`"
                      class="text-decoration-none small font-monospace"
                    >
                      {{ hit.uuid }}
                    </RouterLink>
                  </td>
                  <td class="text-truncate" style="max-width: 280px">
                    {{ hit.info }}
                    <span
                      v-if="hit.is_new"
                      class="badge bg-warning text-dark ms-2"
                      >new</span
                    >
                  </td>
                  <td class="text-muted small">{{ hit.orgc_id }}</td>
                  <td class="text-muted small">{{ hit.date }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Rulezet results -->
          <div
            v-else-if="
              hunt.hunt_type === 'rulezet' && displayResult.hits.length
            "
            class="table-responsive"
          >
            <table class="table table-sm table-striped align-middle">
              <thead>
                <tr>
                  <th>format</th>
                  <th>title</th>
                  <th>author</th>
                  <th>date</th>
                  <th>source</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(rule, i) in displayResult.hits" :key="i">
                  <td>
                    <span class="badge bg-secondary font-monospace">{{
                      rule.format ?? "—"
                    }}</span>
                  </td>
                  <td style="max-width: 320px">
                    <a
                      v-if="rule.detail_url"
                      :href="rule.detail_url"
                      target="_blank"
                      rel="noopener"
                      class="text-decoration-none"
                    >
                      {{ rule.title ?? "—" }}
                    </a>
                    <span v-else>{{ rule.title ?? "—" }}</span>
                    <span
                      v-if="rule.is_new"
                      class="badge bg-warning text-dark ms-2"
                      >new</span
                    >
                  </td>
                  <td class="text-muted small text-nowrap">
                    {{ rule.author ?? "—" }}
                  </td>
                  <td class="text-muted small text-nowrap">
                    {{ rule.creation_date ?? "—" }}
                  </td>
                  <td class="small">
                    <a
                      v-if="rule.source"
                      :href="rule.source"
                      target="_blank"
                      rel="noopener"
                      class="text-decoration-none text-truncate d-block"
                      style="max-width: 200px"
                    >
                      {{ rule.source }}
                    </a>
                    <span v-else class="text-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- CPE / vulnerability results -->
          <div
            v-else-if="hunt.hunt_type === 'cpe' && displayResult.hits.length"
            class="table-responsive"
          >
            <table class="table table-sm table-striped align-middle">
              <thead>
                <tr>
                  <th>CVE ID</th>
                  <th>severity</th>
                  <th>description</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(hit, i) in displayResult.hits" :key="i">
                  <td class="text-nowrap">
                    <a
                      :href="`https://vulnerability.circl.lu/vuln/${hit.cve_id}`"
                      target="_blank"
                      rel="noopener"
                      class="text-decoration-none font-monospace"
                    >
                      {{ hit.cve_id }}
                    </a>
                    <span
                      v-if="hit.is_new"
                      class="badge bg-warning text-dark ms-2"
                      >new</span
                    >
                  </td>
                  <td>
                    <span
                      v-if="hit.severity"
                      class="badge"
                      :class="{
                        'bg-danger': ['CRITICAL', 'HIGH'].includes(
                          hit.severity?.toUpperCase(),
                        ),
                        'bg-warning text-dark':
                          hit.severity?.toUpperCase() === 'MEDIUM',
                        'bg-secondary': ['LOW', 'NONE'].includes(
                          hit.severity?.toUpperCase(),
                        ),
                      }"
                    >
                      {{ hit.severity }}
                    </span>
                    <span v-else class="text-muted">—</span>
                  </td>
                  <td class="text-truncate" style="max-width: 400px">
                    {{ hit.description || "—" }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Correlation results -->
          <div
            v-else-if="
              hunt.index_target === 'correlations' && displayResult.hits.length
            "
            class="table-responsive"
          >
            <table class="table table-sm table-striped">
              <thead>
                <tr>
                  <th>source event</th>
                  <th>source attr</th>
                  <th>target value</th>
                  <th>match type</th>
                  <th>score</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(hit, i) in displayResult.hits" :key="i">
                  <td>
                    <RouterLink
                      v-if="hit.source_event_uuid"
                      :to="`/events/${hit.source_event_uuid}`"
                      class="text-decoration-none small font-monospace"
                    >
                      {{ hit.source_event_uuid }}
                    </RouterLink>
                    <span v-else class="text-muted small">—</span>
                    <span
                      v-if="hit.is_new"
                      class="badge bg-warning text-dark ms-2"
                      >new</span
                    >
                  </td>
                  <td>
                    <RouterLink
                      v-if="hit.source_attribute_uuid"
                      :to="`/attributes/${hit.source_attribute_uuid}`"
                      class="text-decoration-none small font-monospace"
                    >
                      {{ hit.source_attribute_uuid }}
                    </RouterLink>
                    <span v-else class="text-muted small">—</span>
                  </td>
                  <td class="text-truncate" style="max-width: 220px">
                    <RouterLink
                      v-if="hit.target_attribute_uuid"
                      :to="`/attributes/${hit.target_attribute_uuid}`"
                      class="text-decoration-none"
                    >
                      {{ hit.target_attribute_value }}
                    </RouterLink>
                    <span v-else>{{ hit.target_attribute_value }}</span>
                  </td>
                  <td>
                    <code class="small">{{ hit.match_type }}</code>
                  </td>
                  <td class="text-muted small">{{ hit.score }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-else-if="displayResult.total === 0"
            class="text-muted text-center py-3"
          >
            No matches found.
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
