<script setup>
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import { useServersStore } from "@/stores";
import DeleteServerModal from "@/components/servers/DeleteServerModal.vue";
import ServerSyncActions from "@/components/servers/ServerSyncActions.vue";

const serversStore = useServersStore();
const { servers, status } = storeToRefs(serversStore);

serversStore.getAll();

function handleServerDeleted() {
  serversStore.getAll();
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="alert alert-danger">
    {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table v-show="!status.loading" class="table table-striped align-middle">
      <thead>
        <tr>
          <th scope="col">server</th>
          <th scope="col" class="d-none d-md-table-cell">sync</th>
          <th scope="col">actions</th>
          <th scope="col" class="text-end">manage</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="server.id" v-for="server in servers">
          <!-- Name + URL -->
          <td>
            <RouterLink
              :to="`/servers/${server.id}`"
              class="fw-semibold text-decoration-none"
            >
              {{ server.name }}
            </RouterLink>
            <div
              class="text-muted small text-truncate"
              style="max-width: 320px"
              :title="server.url"
            >
              {{ server.url }}
            </div>
          </td>

          <!-- Pull / Push enabled badges -->
          <td class="d-none d-md-table-cell">
            <span
              class="badge me-1"
              :class="server.pull ? 'bg-primary' : 'bg-secondary'"
              title="Pull"
            >
              pull
            </span>
            <span
              class="badge"
              :class="server.push ? 'bg-success' : 'bg-secondary'"
              title="Push"
            >
              push
            </span>
          </td>

          <!-- Sync actions: test connection, pull, push, explore -->
          <td>
            <ServerSyncActions :server="server" />
          </td>

          <!-- Edit / View / Delete -->
          <td class="text-end">
            <div class="btn-toolbar float-end" role="toolbar">
              <div class="btn-group btn-group-sm me-2" role="group">
                <RouterLink
                  :to="`/servers/${server.id}`"
                  class="btn btn-outline-primary"
                  title="View"
                >
                  <font-awesome-icon icon="fa-solid fa-eye" />
                </RouterLink>
                <RouterLink
                  :to="`/servers/update/${server.id}`"
                  class="btn btn-outline-primary"
                  title="Edit"
                >
                  <font-awesome-icon icon="fa-solid fa-pen" />
                </RouterLink>
              </div>
              <div class="btn-group btn-group-sm" role="group">
                <button
                  type="button"
                  class="btn btn-danger"
                  data-bs-toggle="modal"
                  :data-bs-target="'#deleteServerModal-' + server.id"
                  title="Delete"
                >
                  <font-awesome-icon icon="fa-solid fa-trash" />
                </button>
              </div>
            </div>
            <DeleteServerModal
              @server-deleted="handleServerDeleted"
              :server_id="server.id"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
