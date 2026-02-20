<script setup>
import { storeToRefs } from "pinia";
import { useTasksStore } from "@/stores";
import TaskListCard from "@/components/tasks/TaskListCard.vue";
import ScheduledTaskListCard from "@/components/tasks/ScheduledTaskListCard.vue";

const tasksStore = useTasksStore();
const { tasks, scheduledTasks } = storeToRefs(tasksStore);

tasksStore.get_tasks();
tasksStore.get_scheduled_tasks();
</script>

<template>
  <div class="container mt-4">
    <ScheduledTaskListCard :scheduledTasks="scheduledTasks" />
    <TaskListCard :tasks="tasks" />
  </div>
</template>
