<script setup>
import { ref, computed, watch } from "vue";
import {
  useTasksStore,
  useFeedsStore,
  useServersStore,
  useUsersStore,
} from "@/stores";
import { storeToRefs } from "pinia";
import ScheduleEditor from "@/components/tasks/ScheduleEditor.vue";

const tasksStore = useTasksStore();
const feedsStore = useFeedsStore();
const serversStore = useServersStore();
const usersStore = useUsersStore();

const { status } = storeToRefs(tasksStore);
const { feeds } = storeToRefs(feedsStore);
const { servers } = storeToRefs(serversStore);
const { users } = storeToRefs(usersStore);

const emit = defineEmits(["scheduled-task-created"]);

const modalEl = ref(null);
defineExpose({ modalEl });

const TASKS = [
  {
    value: "app.worker.tasks.fetch_feed",
    label: "fetch_feed",
    needsFeed: true,
    needsUser: true,
  },
  { value: "app.worker.tasks.load_taxonomies", label: "load_taxonomies" },
  {
    value: "app.worker.tasks.load_galaxies",
    label: "load_galaxies",
    needsUser: true,
  },
  {
    value: "app.worker.tasks.server_pull_by_id",
    label: "server_pull_by_id",
    needsServer: true,
    needsUser: true,
  },
];

const selectedTask = ref(null);
const selectedFeedId = ref(null);
const selectedServerId = ref(null);
const selectedUserId = ref(null);
const scheduleEditorRef = ref(null);
const scheduleValid = ref(false);

const needsFeed = computed(() => !!selectedTask.value?.needsFeed);
const needsServer = computed(() => !!selectedTask.value?.needsServer);
const needsUser = computed(() => !!selectedTask.value?.needsUser);

watch(selectedTask, (task) => {
  selectedFeedId.value = null;
  selectedServerId.value = null;
  selectedUserId.value = null;
  if (task?.needsFeed) feedsStore.getAll();
  if (task?.needsServer) serversStore.getAll();
  if (task?.needsUser) usersStore.getAll();
});

const isValid = computed(() => {
  if (!selectedTask.value) return false;
  if (needsFeed.value && !selectedFeedId.value) return false;
  if (needsServer.value && !selectedServerId.value) return false;
  if (needsUser.value && !selectedUserId.value) return false;
  return scheduleValid.value;
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

function reset() {
  selectedTask.value = null;
  selectedFeedId.value = null;
  selectedServerId.value = null;
  selectedUserId.value = null;
  scheduleEditorRef.value?.reset();
}

async function onSubmit() {
  const result = await tasksStore.create_scheduled_task({
    task_name: selectedTask.value.value,
    params: { kwargs: buildKwargs() },
    schedule: scheduleEditorRef.value.buildSchedule(),
  });
  if (result) {
    emit("scheduled-task-created");
    reset();
  }
}
</script>

<template>
  <div
    ref="modalEl"
    id="createScheduledTaskModal"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="createScheduledTaskModalLabel"
    aria-hidden="true"
  >
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="createScheduledTaskModalLabel">
            New Scheduled Task
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Discard"
          ></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label for="createTaskSelect" class="form-label">Task</label>
            <select
              id="createTaskSelect"
              v-model="selectedTask"
              class="form-select"
            >
              <option :value="null" disabled>Select a task…</option>
              <option v-for="task in TASKS" :key="task.value" :value="task">
                {{ task.label }}
              </option>
            </select>
          </div>

          <div v-if="needsFeed" class="mb-3">
            <label for="createFeedSelect" class="form-label">Feed</label>
            <select
              id="createFeedSelect"
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
            <label for="createServerSelect" class="form-label">Server</label>
            <select
              id="createServerSelect"
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
            <label for="createUserSelect" class="form-label">Run as user</label>
            <select
              id="createUserSelect"
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
            <span v-else>Create</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
