<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import { authHelper } from "@/helpers";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "events:create"),
);
</script>

<template>
  <RouterLink v-if="canCreate" to="/events/add" class="btn btn-primary btn-sm">
    + New Event
  </RouterLink>
</template>
