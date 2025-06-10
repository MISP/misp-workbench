<script setup>
import { useTasksStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faRefresh, faCog } from "@fortawesome/free-solid-svg-icons";
import { useToastsStore } from "@/stores";
import ManageWorkerModal from "@/components/tasks/ManageWorkerModal.vue";

const toastsStore = useToastsStore();
const tasksStore = useTasksStore();

defineProps({
  worker_id: String,
  worker: Object,
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

  tasksStore.get_workers();
}

function handleWorkerUpdate() {
  tasksStore.get_workers();
}
</script>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div class="btn-group me-2" role="group">
      <button
        type="button"
        class="btn btn-outline-primary"
        data-placement="top"
        title="Restart"
        @click="restartWorker(worker_id)"
      >
        <FontAwesomeIcon :icon="faRefresh" />
      </button>
      <button
        type="button"
        class="btn btn-outline-primary"
        data-placement="top"
        title="Mange Worker Pool"
        data-bs-toggle="modal"
        :data-bs-target="'#manageWorkerModal-' + worker_id"
      >
        <FontAwesomeIcon :icon="faCog" />
      </button>
    </div>
    <ManageWorkerModal
      @worker-updated="handleWorkerUpdate"
      :worker_id="worker_id"
      :worker="worker"
    />
  </div>
</template>
