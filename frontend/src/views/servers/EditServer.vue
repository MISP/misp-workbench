<script setup>
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { useRoute } from "vue-router";
import ServerUpdate from "@/components/servers/ServerUpdate.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute();
const serversStore = useServersStore();
const { server, status } = storeToRefs(serversStore);
serversStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <ServerUpdate v-if="!status.loading" :server="server" :status="status" />
  <div v-if="status.error" class="text-danger">
    Error loading server: {{ status.error }}
  </div>
</template>
