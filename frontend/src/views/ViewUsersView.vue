<script setup>
import { storeToRefs } from "pinia";
import { useUsersStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import UserView from "@/components/users/UsersView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute()
const usersStore = useUsersStore();
const { user } = storeToRefs(usersStore);
usersStore.getById(route.params.id);
defineProps(['id']);
</script>

<template>
    <Spinner v-if="user.loading" />
    <UserView v-if="!user.loading" :user="user" />
    <div v-if="user.error" class="text-danger">
        Error loading user: {{ user.error }}
    </div>
</template>