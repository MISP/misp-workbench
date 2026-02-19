<script setup>
import { ref, computed, onMounted } from "vue";
import {
  useTasksStore,
  useFeedsStore,
  useServersStore,
  useUsersStore,
} from "@/stores";
import { storeToRefs } from "pinia";
import { parseScheduleString } from "@/helpers";
import ScheduleEditor from "@/components/tasks/ScheduleEditor.vue";

const tasksStore = useTasksStore();
const feedsStore = useFeedsStore();
const serversStore = useServersStore();
const usersStore = useUsersStore();

const { status } = storeToRefs(tasksStore);
const { feeds } = storeToRefs(feedsStore);
const { servers } = storeToRefs(serversStore);
const { users } = storeToRefs(usersStore);

const props = defineProps({ scheduled_task: Object });
const emit = defineEmits(["scheduled-task-updated"]);

const modalEl = ref(null);
defineExpose({ modalEl });

const TASKS = [
  { value: "app.worker.tasks.fetch_feed", needsFeed: true, needsUser: true },
  { value: "app.worker.tasks.load_taxonomies" },
  { value: "app.worker.tasks.load_galaxies", needsUser: true },
  {
    value: "app.worker.tasks.server_pull_by_id",
    needsServer: true,
    needsUser: true,
  },
];

const taskDef = computed(
  () => TASKS.find((t) => t.value === props.scheduled_task?.task_name) ?? {},
);
const needsFeed = computed(() => !!taskDef.value.needsFeed);
const needsServer = computed(() => !!taskDef.value.needsServer);
const needsUser = computed(() => !!taskDef.value.needsUser);

// Pre-populate kwargs from the existing task; captured once on mount so user edits aren't overwritten.
const selectedFeedId = ref(props.scheduled_task?.kwargs?.feed_id ?? null);
const selectedServerId = ref(props.scheduled_task?.kwargs?.server_id ?? null);
const selectedUserId = ref(props.scheduled_task?.kwargs?.user_id ?? null);

const scheduleEditorRef = ref(null);
const scheduleValid = ref(false);

// Parse the current schedule string once; passed as initialSchedule to ScheduleEditor.
const initialSchedule = parseScheduleString(props.scheduled_task?.schedule);

const isValid = computed(() => {
  if (needsFeed.value && !selectedFeedId.value) return false;
  if (needsServer.value && !selectedServerId.value) return false;
  if (needsUser.value && !selectedUserId.value) return false;
  return scheduleValid.value;
});

onMounted(() => {
  if (needsFeed.value) feedsStore.getAll();
  if (needsServer.value) serversStore.getAll();
  if (needsUser.value) usersStore.getAll();
});

function buildKwargs() {
  const kwargs = {};
  if (needsFeed.value) kwargs.feed_id = selectedFeedId.value;
  if (needsServer.value) {
    kwargs.server_id = selectedServerId.value;
    kwargs.technique = "full";
  }
  if (needsUser.value) kwargs.user_id = selectedUserId.value;
  return kwargs;
}

async function onSubmit() {
  const result = await tasksStore.update_scheduled_task(
    props.scheduled_task.id,
    {
      params: { kwargs: buildKwargs() },
      schedule: scheduleEditorRef.value.buildSchedule(),
    },
  );
  if (result) emit("scheduled-task-updated");
}
</script>

<template>
  <div
    ref="modalEl"
    :id="`configureScheduledTaskModal_${scheduled_task.id}`"
    class="modal fade"
    tabindex="-1"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            Configure
            <code class="text-body-secondary">{{
              scheduled_task.task_name.replace("app.worker.tasks.", "")
            }}</code>
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <div v-if="needsFeed" class="mb-3">
            <label for="cfgFeedSelect" class="form-label">Feed</label>
            <select
              id="cfgFeedSelect"
              v-model="selectedFeedId"
              class="form-select"
            >
              <option :value="null" disabled>Select a feed…</option>
              <option v-for="feed in feeds" :key="feed.id" :value="feed.id">
                #{{ feed.id }} — {{ feed.name }}
              </option>
            </select>
          </div>

          <div v-if="needsServer" class="mb-3">
            <label for="cfgServerSelect" class="form-label">Server</label>
            <select
              id="cfgServerSelect"
              v-model="selectedServerId"
              class="form-select"
            >
              <option :value="null" disabled>Select a server…</option>
              <option
                v-for="server in servers"
                :key="server.id"
                :value="server.id"
              >
                #{{ server.id }} — {{ server.name }}
              </option>
            </select>
          </div>

          <div v-if="needsUser" class="mb-3">
            <label for="cfgUserSelect" class="form-label">Run as user</label>
            <select
              id="cfgUserSelect"
              v-model="selectedUserId"
              class="form-select"
            >
              <option :value="null" disabled>Select a user…</option>
              <option v-for="user in users" :key="user.id" :value="user.id">
                #{{ user.id }} — {{ user.email }}
              </option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label d-block">Schedule</label>
            <ScheduleEditor
              ref="scheduleEditorRef"
              :initialSchedule="initialSchedule"
              @valid-change="scheduleValid = $event"
            />
          </div>
        </div>

        <div
          v-if="status.error"
          class="w-100 alert alert-danger mt-3 mb-0 rounded-0"
        >
          {{ status.error }}
        </div>
        <div class="modal-footer">
          <button
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Discard
          </button>
          <button
            type="submit"
            @click="onSubmit"
            class="btn btn-outline-primary"
            :class="{ disabled: status.loading || !isValid }"
          >
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-else>Save</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
