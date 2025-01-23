<script setup>
import Menu from "./components/menu/Menu.vue";
import { RouterView } from "vue-router";
import { useAuthStore } from "@/stores";
import ToastManager from "./components/misc/ToastManager.vue";

const authStore = useAuthStore();</script>

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
