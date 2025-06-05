<script setup>
import { storeToRefs } from "pinia";
import { useTasksStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import WorkerCard from "@/components/tasks/WorkerCard.vue";
import TaskListCard from "@/components/tasks/TaskListCard.vue";

const tasksStore = useTasksStore();
const { tasks, workers, status } = storeToRefs(tasksStore);

tasksStore.get_workers();
tasksStore.get_tasks();
</script>

<template>
  <Spinner v-if="status.loading" />
  <div class="container mt-4">
    <WorkerCard
      v-for="(worker, name) in workers"
      :key="name"
      :workerName="name"
      :worker="worker"
    />
    <TaskListCard :tasks="tasks" />
  </div>
</template>
