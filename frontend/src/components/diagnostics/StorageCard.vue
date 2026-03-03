<script setup>
import { storeToRefs } from "pinia";
import { useDiagnosticsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

const store = useDiagnosticsStore();
const { storage, status } = storeToRefs(store);
</script>

<template>
  <div class="card my-3 shadow">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0">Attachments Storage</h5>
      <span v-if="storage" class="ms-2 badge bg-secondary">
        {{ storage.engine }}
      </span>
      <span
        v-if="
          storage && storage.connected !== null && storage.engine !== 'local'
        "
        class="ms-2 badge"
        :class="storage.connected ? 'bg-success' : 'bg-danger'"
      >
        {{ storage.connected ? "connected" : "unreachable" }}
      </span>
    </div>
    <div class="card-body">
      <Spinner v-if="status.loading" />

      <div v-if="!status.loading && storage">
        <!-- Local filesystem -->
        <template v-if="storage.engine === 'local'">
          <ul class="list-group list-group-flush small">
            <li class="list-group-item d-flex justify-content-between">
              <span>Path</span>
              <span class="text-muted font-monospace">{{ storage.path }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Directory</span>
              <span
                class="badge"
                :class="
                  storage.path_exists ? 'bg-success' : 'bg-warning text-dark'
                "
              >
                {{ storage.path_exists ? "exists" : "missing" }}
              </span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Objects</span>
              <span class="text-muted">{{
                storage.object_count?.toLocaleString()
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Used by attachments</span>
              <span class="text-muted">{{ storage.total_size_human }}</span>
            </li>
            <li
              v-if="storage.disk_total"
              class="list-group-item d-flex justify-content-between"
            >
              <span>Disk usage</span>
              <span class="text-muted">
                {{ storage.disk_used }} / {{ storage.disk_total }} ({{
                  storage.disk_used_percent
                }}%)
              </span>
            </li>
            <li
              v-if="storage.disk_free"
              class="list-group-item d-flex justify-content-between"
            >
              <span>Disk free</span>
              <span class="text-muted">{{ storage.disk_free }}</span>
            </li>
          </ul>
        </template>

        <!-- S3 / Garage -->
        <template v-else>
          <div v-if="!storage.connected" class="alert alert-danger mb-0">
            {{ storage.error }}
          </div>

          <ul class="list-group list-group-flush small">
            <li class="list-group-item d-flex justify-content-between">
              <span>Endpoint</span>
              <span class="text-muted font-monospace">{{
                storage.endpoint
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>Bucket</span>
              <span class="text-muted font-monospace">{{
                storage.bucket
              }}</span>
            </li>
            <li class="list-group-item d-flex justify-content-between">
              <span>TLS</span>
              <span class="text-muted">{{
                storage.secure ? "enabled" : "disabled"
              }}</span>
            </li>
            <template v-if="storage.connected">
              <li class="list-group-item d-flex justify-content-between">
                <span>Objects</span>
                <span class="text-muted">{{
                  storage.object_count?.toLocaleString()
                }}</span>
              </li>
              <li class="list-group-item d-flex justify-content-between">
                <span>Total size</span>
                <span class="text-muted">{{ storage.total_size_human }}</span>
              </li>
            </template>
          </ul>
        </template>
      </div>
    </div>
  </div>
</template>
