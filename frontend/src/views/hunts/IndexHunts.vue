<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useHuntsStore, useTasksStore, useAuthStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import AddHuntModal from "@/components/hunts/AddHuntModal.vue";
import HuntActions from "@/components/hunts/HuntActions.vue";
import HuntSparkline from "@/components/hunts/HuntSparkline.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { formatSchedule, authHelper } from "@/helpers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const huntsStore = useHuntsStore();
const tasksStore = useTasksStore();
const authStore = useAuthStore();
const { hunts, status } = storeToRefs(huntsStore);
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "hunts:create"),
);
const { scheduledTasks } = storeToRefs(tasksStore);

huntsStore.getAll();
tasksStore.get_scheduled_tasks();

function huntSchedule(huntId) {
  return scheduledTasks.value.find((t) => t.kwargs?.hunt_id === huntId) ?? null;
}

const addModalOpen = ref(false);

function onHuntCreated() {
  addModalOpen.value = false;
  huntsStore.getAll();
}
</script>

<template>
  <div class="d-flex justify-content-between align-items-center mb-3">
    <button
      v-if="canCreate"
      class="btn btn-primary btn-sm"
      @click="addModalOpen = true"
    >
      + New Hunt
    </button>
  </div>

  <Spinner v-if="status.loading" />

  <div
    v-else-if="hunts && hunts.items && hunts.items.length === 0"
    class="text-muted"
  >
    No hunts yet.<template v-if="canCreate">
      Create one to get started.</template
    >
  </div>

  <div v-else-if="hunts && hunts.items" class="table-responsive">
    <table class="table table-striped text-start align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th class="d-none d-xl-table-cell">target</th>
          <th class="d-none d-md-table-cell">last run</th>
          <th class="d-none d-lg-table-cell">frequency</th>
          <th class="d-none d-md-table-cell">matches</th>
          <th class="text-end">status</th>
          <th class="text-end"><span class="visually-hidden">actions</span></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="hunt in hunts.items" :key="hunt.id">
          <!-- Takes the room the other columns leave; the query truncates. -->
          <td class="hunt-name">
            <RouterLink
              :to="`/hunts/${hunt.id}`"
              class="fw-semibold text-decoration-none text-break"
            >
              {{ hunt.name }}
            </RouterLink>
            <div
              class="text-muted small text-truncate font-monospace"
              :title="hunt.query"
            >
              {{ hunt.query }}
            </div>
          </td>
          <td class="d-none d-xl-table-cell">
            <span class="badge bg-secondary">{{
              hunt.hunt_type === "opensearch"
                ? hunt.index_target
                : hunt.hunt_type
            }}</span>
          </td>
          <td class="d-none d-md-table-cell text-muted small text-nowrap">
            {{
              hunt.last_run_at
                ? dayjs.utc(hunt.last_run_at).local().fromNow()
                : "never"
            }}
          </td>
          <td class="d-none d-lg-table-cell text-muted small">
            <template v-if="huntSchedule(hunt.id)">
              {{ formatSchedule(huntSchedule(hunt.id).schedule) }}
            </template>
            <span v-else>manual</span>
          </td>
          <td class="d-none d-md-table-cell">
            <HuntSparkline :hunt-id="hunt.id" :last-run-at="hunt.last_run_at" />
          </td>
          <td class="text-end">
            <span
              class="badge"
              :class="hunt.status === 'active' ? 'bg-success' : 'bg-secondary'"
            >
              {{ hunt.status }}
            </span>
          </td>
          <td class="text-end">
            <HuntActions
              :hunt="hunt"
              @deleted="huntsStore.getAll()"
              @ran="(updated) => Object.assign(hunt, updated)"
              @toggled="(updated) => Object.assign(hunt, updated)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <AddHuntModal
    v-if="addModalOpen"
    @created="onHuntCreated"
    @close="addModalOpen = false"
  />
</template>

<style scoped>
/* The usual table truncation: a cell sized to what the others leave, so
   its contents can be cut with an ellipsis rather than widen the table. */
.hunt-name {
  width: 100%;
  max-width: 0;
}
</style>
