<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import { useHuntsStore, useTasksStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import AddHuntModal from "@/components/hunts/AddHuntModal.vue";
import HuntActions from "@/components/hunts/HuntActions.vue";
import HuntSparkline from "@/components/hunts/HuntSparkline.vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import { formatSchedule } from "@/helpers";

dayjs.extend(relativeTime);
dayjs.extend(utc);

const huntsStore = useHuntsStore();
const tasksStore = useTasksStore();
const { hunts, status } = storeToRefs(huntsStore);
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
    <button class="btn btn-primary btn-sm" @click="addModalOpen = true">
      + New Hunt
    </button>
  </div>

  <Spinner v-if="status.loading" />

  <div
    v-else-if="hunts && hunts.items && hunts.items.length === 0"
    class="text-muted"
  >
    No hunts yet. Create one to get started.
  </div>

  <div v-else-if="hunts && hunts.items" class="table-responsive">
    <table class="table table-striped text-start align-middle">
      <thead>
        <tr>
          <th>name</th>
          <th v-if="!$isMobile">target</th>
          <th v-if="!$isMobile">last run</th>
          <th v-if="!$isMobile">frequency</th>
          <th v-if="!$isMobile">matches</th>
          <th class="text-end">status</th>
          <th class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="hunt in hunts.items" :key="hunt.id">
          <td>
            <RouterLink
              :to="`/hunts/${hunt.id}`"
              class="fw-semibold text-decoration-none"
            >
              {{ hunt.name }}
            </RouterLink>
            <div
              class="text-muted small text-truncate font-monospace"
              style="max-width: 320px"
              :title="hunt.query"
            >
              {{ hunt.query }}
            </div>
          </td>
          <td v-if="!$isMobile">
            <span class="badge bg-secondary">{{ hunt.index_target }}</span>
          </td>
          <td v-if="!$isMobile" class="text-muted small">
            {{
              hunt.last_run_at
                ? dayjs.utc(hunt.last_run_at).local().fromNow()
                : "never"
            }}
          </td>
          <td v-if="!$isMobile" class="text-muted small">
            <template v-if="huntSchedule(hunt.id)">
              {{ formatSchedule(huntSchedule(hunt.id).schedule) }}
            </template>
            <span v-else>manual</span>
          </td>
          <td v-if="!$isMobile">
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
