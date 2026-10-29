<script setup>
import { storeToRefs } from "pinia";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useDiagnosticsStore } from "@/stores";

dayjs.extend(relativeTime);

const store = useDiagnosticsStore();
const { queues } = storeToRefs(store);

const QUEUE_DESCRIPTIONS = {
  celery: "User-triggered work",
  maintenance: "Frequent periodic jobs",
  bulk: "Rebuilds and reloads",
  ingest: "Feed fetches and server pulls",
  sinks: "Deliveries to sinks",
  reactor_sandbox: "Reactor scripts",
  lab_kernel: "Tech Lab notebook kernels",
};

const STATUS_CLASSES = {
  queued: "bg-secondary",
  running: "bg-primary",
};

function sourceLink(run) {
  return run.kind === "feed"
    ? `/feeds/${run.source_id}`
    : `/servers/${run.source_id}`;
}

function progress(run) {
  if (!run.total) return "listing events";
  return `${run.done + run.failed} / ${run.total}`;
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">Queues</h5>
      <span
        v-if="queues?.ingest?.paused"
        class="ms-2 badge bg-warning text-dark"
        title="Runtime settings, ingest"
      >
        ingestion paused
      </span>
    </div>
    <div class="card-body">
      <div v-if="queues && !queues.connected" class="alert alert-danger mb-0">
        {{ queues.error }}
      </div>

      <template v-else-if="queues">
        <div class="table-responsive-sm">
          <table class="table table-sm align-middle small">
            <thead>
              <tr>
                <th scope="col">queue</th>
                <th scope="col" class="text-end">waiting</th>
                <th scope="col">workers</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="queue in queues.queues" :key="queue.name">
                <td>
                  <code>{{ queue.name }}</code>
                  <div class="text-muted">
                    {{ QUEUE_DESCRIPTIONS[queue.name] }}
                  </div>
                </td>
                <td class="text-end">{{ queue.pending }}</td>
                <td>
                  <span
                    v-if="!queue.workers.length"
                    class="badge bg-danger"
                    title="Nothing consumes this queue: its tasks never run"
                    >no worker</span
                  >
                  <span
                    v-for="worker in queue.workers"
                    :key="worker"
                    class="badge bg-light text-dark border me-1"
                    >{{ worker }}</span
                  >
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h6 class="mt-3">
          Ingestion runs
          <span class="text-muted small fw-normal">
            ({{
              queues.ingest.max_concurrent_runs
                ? `${queues.ingest.max_concurrent_runs} at a time`
                : "no limit"
            }})
          </span>
        </h6>
        <p v-if="!queues.ingest.runs.length" class="text-muted small mb-0">
          No feed fetch or server pull in progress.
        </p>
        <ul v-else class="list-group list-group-flush small">
          <li
            v-for="run in queues.ingest.runs"
            :key="`${run.kind}:${run.source_id}`"
            class="list-group-item d-flex align-items-center gap-2"
          >
            <span class="badge" :class="STATUS_CLASSES[run.status]">
              {{ run.status }}
            </span>
            <span class="text-muted">{{ run.kind }}</span>
            <RouterLink :to="sourceLink(run)" class="me-auto">
              {{ run.name || `#${run.source_id}` }}
            </RouterLink>
            <span class="text-muted">{{ progress(run) }}</span>
            <span class="text-muted">
              {{ dayjs.unix(run.started_at || run.queued_at).fromNow() }}
            </span>
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
