<script setup>
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { useRoute } from "vue-router";
import ServerExplorer from "@/components/servers/ServerExplorer.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const serversStore = useServersStore();
const { server, status } = storeToRefs(serversStore);
serversStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <ServerExplorer v-if="!status.loading" :server="server" />
  <div v-if="status.error" class="text-danger">
    Error loading server: {{ status.error }}
  </div>
</template>
