<script setup>
import { onMounted, onBeforeUnmount } from "vue";
import { storeToRefs } from "pinia";
import { useTasksStore } from "@/stores";
import TaskListCard from "@/components/tasks/TaskListCard.vue";
import ActiveTaskListCard from "@/components/tasks/ActiveTaskListCard.vue";
import ScheduledTaskListCard from "@/components/tasks/ScheduledTaskListCard.vue";

const ACTIVE_TASKS_POLL_MS = 5000;

const tasksStore = useTasksStore();
const { tasks, activeTasks, scheduledTasks } = storeToRefs(tasksStore);

tasksStore.get_tasks();
tasksStore.get_scheduled_tasks();
tasksStore.get_active_tasks();

let activeTasksInterval = null;
onMounted(() => {
  activeTasksInterval = setInterval(
    () => tasksStore.get_active_tasks(),
    ACTIVE_TASKS_POLL_MS,
  );
});
onBeforeUnmount(() => {
  if (activeTasksInterval) clearInterval(activeTasksInterval);
});
</script>

<template>
  <div class="container mt-4">
    <ScheduledTaskListCard :scheduledTasks="scheduledTasks" />
    <ActiveTaskListCard :activeTasks="activeTasks" />
    <TaskListCard :tasks="tasks" />
  </div>
</template>
