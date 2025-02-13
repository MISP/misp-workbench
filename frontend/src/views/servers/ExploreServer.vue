<script setup>
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { useRoute } from "vue-router";
import ServerExplorer from "@/components/servers/ServerExplorer.vue";
import Spinner from "@/components/misc/Spinner.vue";
import ApiError from "@/components/misc/ApiError.vue";

const route = useRoute();
const serversStore = useServersStore();
const { server, status } = storeToRefs(serversStore);
serversStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <ServerExplorer v-if="!status.loading" :server="server" />
  <div
    v-if="status.error"
    class="w-100 alert alert-danger mt-3 mb-3 text-center"
  >
    <ApiError :errors="status.error" />
  </div>
</template>
