<script setup lang="ts">
import { onMounted } from "vue";
import Menu from "./components/menu/Menu.vue";
import { RouterView } from "vue-router";
import { useAuthStore, useUserSettingsStore } from "@/stores";
import ToastManager from "./components/misc/ToastManager.vue";

const authStore = useAuthStore();
const userSettingsStore = useUserSettingsStore();
onMounted(() => {
  if (authStore.isAuthenticated()) {
    userSettingsStore.getAll();
  }
});
</script>

<template>
  <div class="app-container">
    <ToastManager />
    <Menu v-if="authStore.isAuthenticated()" />
    <div class="container-fluid pt-4 pb-4">
      <RouterView />
    </div>
  </div>
</template>

<style>
#app {
  margin: 0 auto;
  font-weight: normal;
}

.pagination {
  justify-content: center;
}

ul.pagination {
  margin-bottom: 0;
}
</style>
