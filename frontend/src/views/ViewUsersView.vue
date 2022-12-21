<script setup>
import { storeToRefs } from "pinia";
import { useUsersStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import UserView from "@/components/users/UserView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute()
const usersStore = useUsersStore();
const { user, status } = storeToRefs(usersStore);
usersStore.getById(route.params.id);
defineProps(['id']);
</script>

<template>
    <Spinner v-if="status.loading" />
    <UserView v-if="!status.loading" :user="user" />
    <div v-if="status.error" class="text-danger">
        Error loading user: {{ status.error }}
    </div>
</template>