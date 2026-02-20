<script setup>
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { redis, status } = storeToRefs(store);

function formatUptime(seconds) {
  if (seconds == null) return "?";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m ${s}s`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function hitRate(hits, misses) {
  if (hits == null || misses == null) return null;
  const total = hits + misses;
  if (total === 0) return null;
  return ((hits / total) * 100).toFixed(1);
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">Redis</h5>
      <span
        v-if="redis"
        class="ms-2 badge"
        :class="redis.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ redis.connected ? "connected" : "unreachable" }}
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && redis">
        <div v-if="!redis.connected" class="alert alert-danger mb-0">
          {{ redis.error }}
        </div>

        <template v-else>
          <!-- Stats -->
          <ul class="list-group list-group-flush small mb-3">
            <li class="list-group-item d-flex justify-content-between">
              <span>Version</span>
              <span class="text-muted"
                >{{ redis.version }} ({{ redis.mode }})</span
              >
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Uptime</span>
              <span class="text-muted">{{
                formatUptime(redis.uptime_seconds)
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Connected clients</span>
              <span class="text-muted">{{ redis.connected_clients }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Blocked clients</span>
              <span class="text-muted">{{ redis.blocked_clients }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Memory used</span>
              <span class="text-muted"
                >{{ redis.memory_used }} / {{ redis.memory_peak }} peak</span
              >
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Memory fragmentation ratio</span>
              <span class="text-muted">{{
                redis.memory_fragmentation_ratio
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Total commands processed</span>
              <span class="text-muted">{{
                redis.total_commands_processed?.toLocaleString()
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Total connections received</span>
              <span class="text-muted">{{
                redis.total_connections_received?.toLocaleString()
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Keyspace hits / misses</span>
              <span class="text-muted">
                {{ redis.keyspace_hits?.toLocaleString() }} /
                {{ redis.keyspace_misses?.toLocaleString() }}
                <span
                  v-if="
                    hitRate(redis.keyspace_hits, redis.keyspace_misses) !== null
                  "
                >
                  ({{ hitRate(redis.keyspace_hits, redis.keyspace_misses) }}%
                  hit rate)
                </span>
              </span>
            </li>
          </ul>

          <!-- Keyspace -->
          <div class="card mt-2">
            <div class="card-header">
              <h6 class="mb-0">Keyspace</h6>
            </div>
            <div
              v-if="!Object.keys(redis.keyspace).length"
              class="card-body text-muted small"
            >
              No databases with keys.
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table">
                  <tr>
                    <th>Database</th>
                    <th class="text-end">Keys</th>
                    <th class="text-end">Expires</th>
                    <th class="text-end">Avg TTL</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(val, db) in redis.keyspace" :key="db">
                    <td class="text-console">{{ db }}</td>
                    <td class="text-end">{{ val.keys?.toLocaleString() }}</td>
                    <td class="text-end">
                      {{ val.expires?.toLocaleString() }}
                    </td>
                    <td class="text-end">
                      {{ val.avg_ttl != null ? val.avg_ttl + " ms" : "—" }}
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
