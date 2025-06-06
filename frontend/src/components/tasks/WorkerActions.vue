<script setup>
import { useTasksStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faRefresh } from "@fortawesome/free-solid-svg-icons";
import { useToastsStore } from "@/stores";

const toastsStore = useToastsStore();
const tasksStore = useTasksStore();

defineProps({
  worker_id: String,
});

function restartWorker(worker_id) {
  tasksStore
    .restart_worker(worker_id)
    .then((response) => {
      if (response.error) {
        toastsStore.push(response.error, "error");
        return;
      } else {
        toastsStore.push(response.message);
      }
    })
    .catch((error) => {
      toastsStore.push(response, "error");
      console.error("Error restarting worker:", error);
    });
}
</script>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-success"
        data-placement="top"
        title="Restart"
        @click="restartWorker(worker_id)"
      >
        <FontAwesomeIcon :icon="faRefresh" />
      </button>
    </div>
  </div>
</template>
