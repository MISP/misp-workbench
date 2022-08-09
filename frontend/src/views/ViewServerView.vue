<script setup>
import { storeToRefs } from "pinia";
import { useServersStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import ServerView from "@/components/servers/ServerView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute()
const serversStore = useServersStore();
const { server } = storeToRefs(serversStore);
serversStore.getById(route.params.id);
defineProps(['id']);
</script>

<template>
    <Spinner v-if="server.loading" />
    <ServerView v-if="!server.loading" :server="server" />
    <div v-if="server.error" class="text-danger">
        Error loading server: {{ server.error }}
    </div>
</template>