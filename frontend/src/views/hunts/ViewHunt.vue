<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useHuntsStore, useTasksStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTime from "dayjs/plugin/relativeTime";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faArrowLeft, faPen } from "@fortawesome/free-solid-svg-icons";

dayjs.extend(utc);
dayjs.extend(relativeTime);

const props = defineProps({ id: { type: String, required: true } });

const huntsStore = useHuntsStore();
const tasksStore = useTasksStore();
const toastsStore = useToastsStore();
const { hunt, status } = storeToRefs(huntsStore);

const runResult = ref(null);
const runError = ref(null);

const scheduleInterval = ref("86400");
const scheduleError = ref(null);
const scheduling = ref(false);

huntsStore.getById(props.id);

async function saveSchedule() {
  if (scheduleInterval.value === "disabled") {
    toastsStore.push(
      "Use the Tasks view to remove an existing schedule.",
      "info",
    );
    return;
  }
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
    .then(() => toastsStore.push("Hunt scheduled successfully.", "success"))
    .catch((err) => (scheduleError.value = err?.message || String(err)))
    .finally(() => (scheduling.value = false));
}

async function runHunt() {
  runResult.value = null;
  runError.value = null;
  await huntsStore
    .run(props.id)
    .then((result) => {
      runResult.value = result;
      // update local match count
      if (hunt.value) {
        hunt.value.last_match_count = result.total;
        hunt.value.last_run_at = new Date().toISOString();
      }
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
          <div class="text-muted small mb-1">Query</div>
          <code class="d-block p-2 bg-body-secondary rounded">{{
            hunt.query
          }}</code>
        </div>
      </div>
    </div>

    <!-- Schedule section -->
    <div class="card mb-3">
      <div class="card-body">
        <div
          class="d-flex justify-content-between align-items-center gap-3 flex-wrap"
        >
          <div>
            <strong>Schedule</strong>
            <div class="text-muted small">
              Automatically re-run this hunt at a fixed interval.
            </div>
          </div>
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
        </div>
        <div v-if="scheduleError" class="alert alert-danger mt-3 mb-0 small">
          {{ scheduleError }}
        </div>
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

        <template v-if="runResult">
          <hr />
          <div class="d-flex gap-4 mb-3">
            <div>
              <span class="fs-3 fw-bold">{{ runResult.total }}</span>
              <div class="text-muted small">total matches</div>
            </div>
            <div>
              <span class="fs-3 fw-bold text-primary">{{
                runResult.hits.length
              }}</span>
              <div class="text-muted small">shown (max 100)</div>
            </div>
          </div>

          <!-- Attribute results -->
          <div
            v-if="hunt.index_target === 'attributes' && runResult.hits.length"
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
                <tr v-for="(hit, i) in runResult.hits" :key="i">
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
            v-else-if="hunt.index_target === 'events' && runResult.hits.length"
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
                <tr v-for="(hit, i) in runResult.hits" :key="i">
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
                  </td>
                  <td class="text-muted small">{{ hit.orgc_id }}</td>
                  <td class="text-muted small">{{ hit.date }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div
            v-else-if="runResult.total === 0"
            class="text-muted text-center py-3"
          >
            No matches found.
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
