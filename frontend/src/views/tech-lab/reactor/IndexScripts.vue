<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useReactorStore, useAuthStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import { authHelper } from "@/helpers";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const reactorStore = useReactorStore();
const authStore = useAuthStore();
const { scripts, status } = storeToRefs(reactorStore);
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "reactor:create"),
);

reactorStore.getAll();

function describeTriggers(triggers) {
  if (!triggers || triggers.length === 0) return "—";
  return triggers.map((t) => `${t.resource_type}.${t.action}`).join(", ");
}
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <h4 class="mb-0">Reactor Scripts</h4>
      <small class="text-muted">
        Tech Lab — Python scripts triggered by events / attributes / objects /
        correlations / sightings.
      </small>
    </div>
    <RouterLink
      v-if="canCreate"
      to="/tech-lab/reactor/add"
      class="btn btn-primary btn-sm"
    >
      + New Reactor Script
    </RouterLink>
  </div>

  <Spinner v-if="status.loading" />

  <div
    v-else-if="scripts && scripts.items && scripts.items.length === 0"
    class="text-muted"
  >
    No reactor scripts yet.<template v-if="canCreate">
      Create one to react to MISP events.</template
    >
  </div>

  <div v-else-if="scripts && scripts.items" class="table-responsive">
    <table class="table table-striped text-start align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th>triggers</th>
          <th>last run</th>
          <th class="text-end">status</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="script in scripts.items" :key="script.id">
          <td>
            <RouterLink
              :to="`/tech-lab/reactor/${script.id}`"
              class="fw-semibold text-decoration-none"
            >
              {{ script.name }}
            </RouterLink>
            <div v-if="script.description" class="text-muted small">
              {{ script.description }}
            </div>
          </td>
          <td class="font-monospace small">
            {{ describeTriggers(script.triggers) }}
          </td>
          <td class="text-muted small">
            <template v-if="script.last_run_at">
              {{ dayjs.utc(script.last_run_at).local().fromNow() }}
              <span
                class="badge ms-1"
                :class="
                  script.last_run_status === 'success'
                    ? 'bg-success'
                    : script.last_run_status === 'failed' ||
                        script.last_run_status === 'timed_out'
                      ? 'bg-danger'
                      : 'bg-secondary'
                "
                >{{ script.last_run_status }}</span
              >
            </template>
            <template v-else>never</template>
          </td>
          <td class="text-end">
            <span
              class="badge"
              :class="
                script.status === 'active' ? 'bg-success' : 'bg-secondary'
              "
              >{{ script.status }}</span
            >
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
