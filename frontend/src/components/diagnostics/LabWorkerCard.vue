<script setup>
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { lab, status } = storeToRefs(store);

function formatUptime(seconds) {
  if (seconds == null) return "?";
  const s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${r}s`;
  if (m > 0) return `${m}m ${r}s`;
  return `${r}s`;
}

function formatIdle(seconds) {
  if (seconds == null) return "?";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">Lab worker</h5>
      <span
        v-if="lab"
        class="ms-2 badge"
        :class="lab.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ lab.connected ? "online" : "offline" }}
      </span>
      <span
        v-if="lab && lab.connected"
        class="ms-2 badge bg-secondary"
        :title="`Idle eviction after ${lab.idle_seconds_threshold}s`"
      >
        {{ lab.kernel_count }}
        kernel{{ lab.kernel_count === 1 ? "" : "s" }}
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && lab">
        <div v-if="!lab.connected" class="alert alert-danger mb-0">
          {{ lab.error || "lab-worker unreachable" }}
        </div>

        <template v-else>
          <!-- Worker stats -->
          <ul class="list-group list-group-flush small mb-3">
            <li class="list-group-item d-flex justify-content-between">
              <span>Worker</span>
              <span class="text-muted">{{ lab.worker?.name }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Pool</span>
              <span class="text-muted">
                {{ lab.worker?.pool_implementation || "?" }}
                ({{ lab.worker?.concurrency ?? "?" }} threads)
              </span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Uptime</span>
              <span class="text-muted">
                {{ formatUptime(lab.worker?.uptime_seconds) }}
              </span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Idle eviction threshold</span>
              <span class="text-muted">
                {{ formatIdle(lab.idle_seconds_threshold) }}
              </span>
            </li>
          </ul>

          <!-- Kernels -->
          <div class="card mt-2">
            <div class="card-header">
              <h6 class="mb-0">Jupyter kernels</h6>
            </div>
            <div v-if="!lab.kernels?.length" class="card-body text-muted small">
              No running kernels.
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table">
                  <tr>
                    <th>User ID</th>
                    <th>Notebook ID</th>
                    <th>Working dir</th>
                    <th class="text-end">Idle</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="k in lab.kernels"
                    :key="`${k.user_id}-${k.notebook_id}`"
                  >
                    <td class="text-console">{{ k.user_id }}</td>
                    <td class="text-console">{{ k.notebook_id }}</td>
                    <td class="text-console">{{ k.cwd }}</td>
                    <td class="text-end">{{ formatIdle(k.idle_seconds) }}</td>
                    <td>
                      <span
                        class="badge"
                        :class="k.started ? 'bg-success' : 'bg-warning'"
                      >
                        {{ k.started ? "ready" : "starting" }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
