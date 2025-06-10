<script setup>
import { useTasksStore } from "@/stores";
import { storeToRefs } from "pinia";

const tasksStore = useTasksStore();
const { status } = storeToRefs(tasksStore);

const props = defineProps({
  worker_id: String,
  worker: Object,
});

const emit = defineEmits(["worker-updated"]);

import { ref } from "vue";

const pool_size = ref(props.worker.stats.pool["max-concurrency"] || 1);

const autoscale = ref({
  enabled: false,
  min: 1,
  max: 10,
});

function onSubmit() {
  if (autoscale.value.enabled) {
    return tasksStore
      .autoscale_worker(
        props.worker_id,
        autoscale.value.min,
        autoscale.value.max,
      )
      .then(() => {
        emit("worker-updated", { worker_id: props.worker_id });
        document.getElementById("closeModalButton").click();
      })
      .catch((error) => (status.error = error));
  } else {
    if (pool_size.value == props.worker.stats.pool["max-concurrency"]) {
      document.getElementById("closeModalButton").click();
      return;
    }

    if (pool_size.value > props.worker.stats.pool["max-concurrency"]) {
      return tasksStore
        .grow_worker(
          props.worker_id,
          props.worker.stats.pool["max-concurrency"] + pool_size.value,
        )
        .then(() => {
          emit("worker-updated", { worker_id: props.worker_id });
          document.getElementById("closeModalButton").click();
        })
        .catch((error) => (status.error = error));
    } else {
      return tasksStore
        .shrink_worker(
          props.worker_id,
          props.worker.stats.pool["max-concurrency"] - pool_size.value,
        )
        .then(() => {
          emit("worker-updated", { worker_id: props.worker_id });
          document.getElementById("closeModalButton").click();
        })
        .catch((error) => (status.error = error));
    }
  }
}
</script>

<template>
  <div
    :id="'manageWorkerModal-' + worker_id"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="manageWorkerModal"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-lg">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title" id="manageWorkerModal">
            Manage Worker #{{ worker_id }}
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
            <label class="form-label fw-bold col-12">Resize Pool</label>
            <input
              type="number"
              class="form-control"
              id="pool_size"
              v-model="pool_size"
              min="1"
              :disabled="autoscale.enabled"
            />
          </div>
          <div>
            <label class="form-label fw-bold">Autoscale</label>
            <div class="row g-2 align-items-center">
              <div class="col-12">
                <input
                  v-model.number="autoscale.enabled"
                  type="checkbox"
                  class="form-check-input"
                />
                <label class="form-check-label ms-2">Enable Autoscale</label>
              </div>
              <div class="col-5">
                <input
                  v-model.number="autoscale.min"
                  type="number"
                  min="1"
                  class="form-control"
                  placeholder="Min"
                  :disabled="!autoscale.enabled"
                />
              </div>
              <div class="col-5">
                <input
                  v-model.number="autoscale.max"
                  type="number"
                  :min="autoscale.min"
                  class="form-control"
                  placeholder="Max"
                  :disabled="!autoscale.enabled"
                />
              </div>
            </div>
            <small class="text-muted">Min/Max concurrent workers</small>
          </div>
        </div>
        <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
          {{ status.error }}
        </div>
        <div class="modal-footer">
          <button
            id="closeModalButton"
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
            :class="{ disabled: status.loading }"
          >
            <span v-if="status.loading">
              <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
              ></span>
            </span>
            <span v-if="!status.loading">Save</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
