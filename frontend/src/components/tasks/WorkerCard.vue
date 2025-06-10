<script setup>
import WorkerActions from "@/components/tasks/WorkerActions.vue";

defineProps({
  workerName: String,
  worker: Object,
});
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex">
      <h5 class="mb-0">{{ workerName }}</h5>
      <div class="ms-auto">
        <WorkerActions :worker_id="workerName" :worker="worker" />
      </div>
    </div>
    <div class="card-body">
      <div class="row mb-3">
        <div class="col-md-6">
          <h6>Stats</h6>
          <ul class="list-group list-group-flush small">
            <li class="list-group-item">PID: {{ worker.stats.pid }}</li>
            <li class="list-group-item">
              Uptime: {{ worker.stats.uptime }} sec
            </li>
            <li class="list-group-item">Clock: {{ worker.stats.clock }}</li>
            <li class="list-group-item">
              Concurrency: {{ worker.stats.pool["max-concurrency"] }}
            </li>
            <li class="list-group-item">
              Prefetch Count: {{ worker.stats.prefetch_count }}
            </li>
          </ul>
        </div>

        <div class="col-md-6">
          <h6>Broker</h6>
          <ul class="list-group list-group-flush small">
            <li class="list-group-item">
              Host: {{ worker.stats.broker.hostname }}
            </li>
            <li class="list-group-item">
              Port: {{ worker.stats.broker.port }}
            </li>
            <li class="list-group-item">
              Transport: {{ worker.stats.broker.transport }}
            </li>
            <li class="list-group-item">
              User: {{ worker.stats.broker.userid }}
            </li>
            <li class="list-group-item">
              Heartbeat: {{ worker.stats.broker.heartbeat }}
            </li>
          </ul>
        </div>
      </div>

      <div class="mb-3">
        <button
          class="btn btn-outline-secondary btn-sm mb-2"
          type="button"
          data-bs-toggle="collapse"
          :data-bs-target="'#tasks-' + workerName"
          aria-expanded="false"
          :aria-controls="'tasks-' + workerName"
        >
          Show Registered Tasks ({{ worker.registered.length }})
        </button>
        <div class="collapse" :id="'tasks-' + workerName">
          <ul class="list-group small">
            <li
              v-for="task in worker.registered"
              :key="task"
              class="list-group-item"
            >
              {{ task }}
            </li>
          </ul>
        </div>
      </div>

      <div>
        <h6>Active Queues</h6>
        <ul class="list-group small">
          <li
            v-for="queue in worker.active_queues"
            :key="queue.name"
            class="list-group-item"
          >
            <strong>{{ queue.name }}</strong> – Routing Key:
            {{ queue.routing_key }} – Exchange: {{ queue.exchange.name }}
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
