<script setup>
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { opensearch, status } = storeToRefs(store);

const statusBadgeClass = (s) =>
  ({ green: "bg-success", yellow: "bg-warning text-dark", red: "bg-danger" })[
    s
  ] ?? "bg-secondary";

const shardTypeBadgeClass = (prirep) =>
  prirep === "p" ? "bg-primary" : "bg-secondary";

const shardStateBadgeClass = (state) =>
  ({
    STARTED: "bg-success",
    UNASSIGNED: "bg-warning text-dark",
    INITIALIZING: "bg-info",
    RELOCATING: "bg-info",
  })[state] ?? "bg-secondary";

const usageBarClass = (pct) => {
  if (pct == null) return "bg-secondary";
  if (pct >= 90) return "bg-danger";
  if (pct >= 70) return "bg-warning";
  return "bg-success";
};
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center justify-content-start">
      <h5 class="mb-0">OpenSearch</h5>
      <span
        v-if="opensearch"
        class="ms-2 badge"
        :class="opensearch.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ opensearch.connected ? "connected" : "unreachable" }}
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && opensearch">
        <!-- Connectivity error -->
        <div v-if="!opensearch.connected" class="alert alert-danger mb-0">
          {{ opensearch.error }}
        </div>

        <template v-else>
          <!-- Cluster health -->
          <h6 class="mb-2">Cluster</h6>
          <ul class="list-group list-group-flush small mb-4">
            <li class="list-group-item d-flex justify-content-between">
              <span>Status</span>
              <span
                class="badge"
                :class="statusBadgeClass(opensearch.cluster.status)"
              >
                {{ opensearch.cluster.status }}
              </span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Cluster name</span>
              <span class="text-muted">{{
                opensearch.cluster.cluster_name
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Nodes</span>
              <span class="text-muted">{{
                opensearch.cluster.number_of_nodes
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Active shards</span>
              <span class="text-muted">{{
                opensearch.cluster.active_shards
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Unassigned shards</span>
              <span class="text-muted">{{
                opensearch.cluster.unassigned_shards
              }}</span>
            </li>
          </ul>

          <!-- Nodes -->
          <div class="card mt-2 mb-3">
            <div class="card-header">
              <h6 class="mb-0">Nodes</h6>
            </div>
            <div
              v-if="!opensearch.nodes.length"
              class="card-body text-muted small"
            >
              No nodes found.
            </div>
            <div v-else>
              <div
                v-for="node in opensearch.nodes"
                :key="node.id"
                class="p-3 border-bottom"
              >
                <div class="fw-semibold small mb-2">{{ node.name }}</div>
                <div class="row g-3 small">
                  <div class="col-md-4">
                    <div class="text-muted mb-1">CPU</div>
                    <div class="progress" style="height: 6px">
                      <div
                        class="progress-bar"
                        :class="usageBarClass(node.cpu_percent)"
                        :style="{ width: (node.cpu_percent ?? 0) + '%' }"
                      />
                    </div>
                    <div class="text-muted mt-1">
                      {{ node.cpu_percent ?? "?" }}%
                    </div>
                  </div>
                  <div class="col-md-4">
                    <div class="text-muted mb-1">Heap (JVM)</div>
                    <div class="progress" style="height: 6px">
                      <div
                        class="progress-bar"
                        :class="usageBarClass(node.heap_used_percent)"
                        :style="{ width: (node.heap_used_percent ?? 0) + '%' }"
                      />
                    </div>
                    <div class="text-muted mt-1">
                      {{ node.heap_used }} / {{ node.heap_max }} ({{
                        node.heap_used_percent ?? "?"
                      }}%)
                    </div>
                  </div>
                  <div class="col-md-4">
                    <div class="text-muted mb-1">Memory (OS)</div>
                    <div class="progress" style="height: 6px">
                      <div
                        class="progress-bar"
                        :class="usageBarClass(node.mem_used_percent)"
                        :style="{ width: (node.mem_used_percent ?? 0) + '%' }"
                      />
                    </div>
                    <div class="text-muted mt-1">
                      {{ node.mem_used }} / {{ node.mem_total }} ({{
                        node.mem_used_percent ?? "?"
                      }}%)
                    </div>
                  </div>
                  <div class="col-md-4">
                    <div class="text-muted mb-1">Disk available</div>
                    <div class="text-muted">
                      {{ node.disk_available }} / {{ node.disk_total }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Indices -->
          <div class="card mt-2 mb-3">
            <div class="card-header">
              <h6 class="mb-0">Indices</h6>
            </div>
            <div
              v-if="opensearch.indices.length === 0"
              class="card-body text-muted small"
            >
              No indices found.
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table">
                  <tr>
                    <th>Index</th>
                    <th>Health</th>
                    <th>Status</th>
                    <th class="text-end">Docs</th>
                    <th class="text-end">Deleted</th>
                    <th class="text-end">Size</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="idx in opensearch.indices" :key="idx.index">
                    <td class="text-console">{{ idx.index }}</td>
                    <td>
                      <span class="badge" :class="statusBadgeClass(idx.health)">
                        {{ idx.health }}
                      </span>
                    </td>
                    <td>{{ idx.status }}</td>
                    <td class="text-end">{{ idx["docs.count"] }}</td>
                    <td class="text-end">{{ idx["docs.deleted"] }}</td>
                    <td class="text-end">{{ idx["store.size"] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Shards -->
          <div class="card mt-2">
            <div class="card-header">
              <h6 class="mb-0">Shards</h6>
            </div>
            <div
              v-if="opensearch.shards.length === 0"
              class="card-body text-muted small"
            >
              No shards found.
            </div>
            <div v-else class="table-responsive">
              <table class="table table-sm table-bordered small mb-0">
                <thead class="table">
                  <tr>
                    <th>Index</th>
                    <th>Shard</th>
                    <th>Type</th>
                    <th>State</th>
                    <th class="text-end">Docs</th>
                    <th class="text-end">Size</th>
                    <th>Node</th>
                    <th>Unassigned reason</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(shard, i) in opensearch.shards" :key="i">
                    <td class="text-console">{{ shard.index }}</td>
                    <td class="text-end">{{ shard.shard }}</td>
                    <td>
                      <span
                        class="badge"
                        :class="shardTypeBadgeClass(shard.prirep)"
                      >
                        {{ shard.prirep === "p" ? "primary" : "replica" }}
                      </span>
                    </td>
                    <td>
                      <span
                        class="badge"
                        :class="shardStateBadgeClass(shard.state)"
                      >
                        {{ shard.state }}
                      </span>
                    </td>
                    <td class="text-end">{{ shard.docs ?? "—" }}</td>
                    <td class="text-end">{{ shard.store ?? "—" }}</td>
                    <td class="text-console">{{ shard.node ?? "—" }}</td>
                    <td class="text-muted">
                      {{ shard["unassigned.reason"] ?? "—" }}
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
