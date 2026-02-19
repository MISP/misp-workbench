<script setup>
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { postgres, status } = storeToRefs(store);

const connBadgeClass = (key) => {
  if (key === "active") return "bg-success";
  if (key === "idle in transaction" || key === "idle in transaction (aborted)")
    return "bg-warning text-dark";
  if (key === "max" || key === "total") return "bg-secondary";
  return "bg-secondary";
};

function shortVersion(v) {
  if (!v) return "?";
  const m = v.match(/PostgreSQL ([\d.]+)/);
  return m ? m[1] : v;
}
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">PostgreSQL</h5>
      <span
        v-if="postgres"
        class="ms-2 badge"
        :class="postgres.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ postgres.connected ? "connected" : "unreachable" }}
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && postgres">
        <div v-if="!postgres.connected" class="alert alert-danger mb-0">
          {{ postgres.error }}
        </div>

        <template v-else>
          <!-- Stats -->
          <ul class="list-group list-group-flush small mb-3">
            <li class="list-group-item d-flex justify-content-between">
              <span>Version</span>
              <span class="text-muted">{{
                shortVersion(postgres.version)
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Database</span>
              <span class="text-console text-muted">{{
                postgres.database
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Database size</span>
              <span class="text-muted">{{ postgres.db_size }}</span>
            </li>
          </ul>

          <!-- Connections -->
          <div class="card mt-2 mb-3">
            <div class="card-header">
              <h6 class="mb-0">Connections</h6>
            </div>
            <div class="card-body p-3">
              <div
                class="progress mb-2"
                style="height: 8px"
                :title="`${postgres.connections.total} / ${postgres.connections.max}`"
              >
                <div
                  class="progress-bar"
                  :class="
                    postgres.connections.total / postgres.connections.max >= 0.9
                      ? 'bg-danger'
                      : postgres.connections.total / postgres.connections.max >=
                          0.7
                        ? 'bg-warning'
                        : 'bg-success'
                  "
                  :style="{
                    width:
                      Math.min(
                        (postgres.connections.total /
                          postgres.connections.max) *
                          100,
                        100,
                      ) + '%',
                  }"
                />
              </div>
              <div class="d-flex flex-wrap gap-2 small">
                <span
                  v-for="(count, state) in postgres.connections"
                  :key="state"
                  class="badge"
                  :class="connBadgeClass(state)"
                >
                  {{ state }}: {{ count }}
                </span>
              </div>
            </div>
          </div>

          <!-- Tables -->
          <div class="card mt-2">
            <div class="card-header">
              <h6 class="mb-0">Tables</h6>
            </div>
            <div
              v-if="!postgres.tables.length"
              class="card-body text-muted small"
            >
              No tables found.
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table">
                  <tr>
                    <th>Table</th>
                    <th class="text-end">Live rows</th>
                    <th class="text-end">Dead rows</th>
                    <th class="text-end">Size</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="t in postgres.tables" :key="t.name">
                    <td class="text-console">{{ t.name }}</td>
                    <td class="text-end">
                      {{ t.live_rows?.toLocaleString() }}
                    </td>
                    <td class="text-end">
                      <span :class="t.dead_rows > 1000 ? 'text-warning' : ''">
                        {{ t.dead_rows?.toLocaleString() }}
                      </span>
                    </td>
                    <td class="text-end">{{ t.size }}</td>
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
