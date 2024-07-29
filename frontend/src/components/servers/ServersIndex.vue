<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import { useServersStore } from "@/stores";
import DeleteServerModal from "@/components/servers/DeleteServerModal.vue";

const serversStore = useServersStore();
const { servers, status } = storeToRefs(serversStore);

serversStore.getAll();

function handleServerDeleted(event) {
    serversStore.getAll();
}

function testServerConnection(server) {
    server.testingConnection = true;
    serversStore
        .testConnection(server.id)
        .then((response) => {
            if (response.status == "ok") {
                server.connectionSucceeded = true;
            } else {
                server.connectionSucceeded = false;
                server.connectionFailed = true;
                server.connectionError = response.error;
            }
            server.testingConnection = false;
        })
        .catch((error) => {
            server.connectionSucceeded = false;
            setErrors({ apiError: error });
        })
        .finally(() => { server.testingConnection = false; });
}

function pullServer(server) {
    serversStore.pull(server.id);
}
</script>

<template>
    <Spinner v-if="status.loading" />
    <div v-if="status.error" class="text-danger">
        Error loading servers: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-show="!status.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">name</th>
                    <th scope="col" v-if="!$isMobile">url</th>
                    <th scope="col" v-if="!$isMobile">org_id</th>
                    <th scope="col">sync actions</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="server.id" v-for="server in servers">
                    <td>
                        <RouterLink :to="`/servers/${server.id}`">{{ server.id }}</RouterLink>
                    </td>
                    <td>{{ server.name }}</td>
                    <td v-if="!$isMobile">{{ server.url }}</td>
                    <td v-if="!$isMobile">{{ server.org_id }}</td>
                    <td>
                        <div class="flex-wrap btn-group" aria-label="Sync Actions">
                            <button
                                v-if="!server.testingConnection && !server.connectionSucceeded && !server.connectionFailed"
                                type="button" class="btn btn-light" @click="testServerConnection(server)"
                                data-toggle="tooltip" data-placement="top" title="Check connection">
                                <font-awesome-icon icon="fa-solid fa-check" />
                            </button>
                            <button v-if="server.testingConnection" type="button" class="btn btn-light">
                                <font-awesome-icon icon="fa-solid fa-sync" spin />
                            </button>
                            <button
                                v-if="!server.testingConnection && server.connectionFailed && !server.connectionSucceeded"
                                type="button" class="btn btn-outline-danger" @click="testServerConnection(server)"
                                data-toggle="tooltip" data-placement="top"
                                :title="'Connection failed: ' + server.connectionError">
                                <font-awesome-icon icon="fa-solid fa-check" />
                            </button>
                            <button v-if="server.connectionSucceeded" type="button" class="btn btn-success"
                                data-toggle="tooltip" data-placement="top" title="Connection succeed">
                                <font-awesome-icon icon="fa-solid fa-check" />
                            </button>
                            <button type="button" class="btn btn-muted" data-toggle="tooltip" data-placement="top"
                                title="Push">
                                <font-awesome-icon icon="fa-solid fa-arrow-up" />
                            </button>
                            <button type="button" class="btn btn-outline-primary" data-placement="top" title="Pull"
                                @click="pullServer(server)">
                                <font-awesome-icon icon="fa-solid fa-arrow-down" />
                            </button>
                        </div>
                    </td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="Server Actions">
                            <button type="button" class="btn btn-outline-danger" data-bs-toggle="modal"
                                :data-bs-target="'#deleteServerModal-' + server.id">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </button>
                            <RouterLink :to="`/servers/update/${server.id}`" tag="button" class="btn btn-outline-primary">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/servers/${server.id}`" tag="button" class="btn btn-outline-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                    <DeleteServerModal @server-deleted="handleServerDeleted" :server_id="server.id" />
                </tr>
            </tbody>
        </table>
    </div>
</template>