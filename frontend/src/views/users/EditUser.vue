<script setup>
import { storeToRefs } from "pinia";
import { useUsersStore } from "@/stores";
import { useRoute } from "vue-router";
import UserUpdate from "@/components/users/UserUpdate.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const usersStore = useUsersStore();
const { user, status } = storeToRefs(usersStore);
usersStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <UserUpdate v-if="!status.loading" :user="user" :status="status" />
  <div v-if="status.error" class="text-danger">
    Error loading user: {{ status.error }}
  </div>
</template>
