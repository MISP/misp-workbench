<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useAuthStore } from "@/stores";
import { authHelper } from "@/helpers";

const authStore = useAuthStore();
const { scopes } = storeToRefs(authStore);

const canCreate = computed(() =>
  authHelper.hasScope(scopes.value, "feeds:create"),
);
</script>

<style></style>
<template>
  <div v-if="canCreate" class="d-flex justify-content-center mx-auto">
    <RouterLink to="/feeds/add">
      <button type="button" class="btn btn-outline-primary">Add Feed</button>
    </RouterLink>
  </div>
</template>
