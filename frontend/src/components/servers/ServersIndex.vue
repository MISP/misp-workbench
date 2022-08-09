<script setup>
import { storeToRefs } from "pinia";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import { useServersStore } from "@/stores";
const serversStore = useServersStore();
const { servers } = storeToRefs(serversStore);
serversStore.getAll();
</script>

<template>
    <Spinner v-if="servers.loading" />
    <div v-if="servers.error" class="text-danger">
        Error loading servers: {{ servers.error }}
    </div>
    <div class="table-responsive-sm">
        <table v-if="!servers.loading" class="table table-striped">
            <thead>
                <tr>
                    <th scope="col">id</th>
                    <th scope="col">name</th>
                    <th scope="col">url</th>
                    <th scope="col">org_id</th>
                    <th scope="col" class="text-end">actions</th>
                </tr>
            </thead>
            <tbody>
                <tr :key="server.id" v-for="server in servers">
                    <td>
                        <RouterLink :to="`/servers/${server.id}`">{{ server.id }}</RouterLink>
                    </td>
                    <td>{{ server.name }}</td>
                    <td>{{ server.url }}</td>
                    <td>{{ server.org_id }}</td>
                    <td class="text-end">
                        <div class="flex-wrap" :class="{ 'btn-group-vertical': $isMobile, 'btn-group': !$isMobile }"
                            aria-label="User Actions">
                            <RouterLink :to="`/servers/delete/${server.id}`" tag="button"
                                class="btn btn-danger disabled">
                                <font-awesome-icon icon="fa-solid fa-trash" />
                            </RouterLink>
                            <RouterLink :to="`/servers/update/${server.id}`" tag="button"
                                class="btn btn-primary disabled">
                                <font-awesome-icon icon="fa-solid fa-pen" />
                            </RouterLink>
                            <RouterLink :to="`/servers/${server.id}`" tag="button" class="btn btn-primary">
                                <font-awesome-icon icon="fa-solid fa-eye" />
                            </RouterLink>
                        </div>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>
</template>