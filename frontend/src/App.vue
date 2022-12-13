<script setup>
import Menu from "./components/menu/Menu.vue";
import { RouterLink, RouterView } from "vue-router";
import { useAuthStore } from "@/stores";

const authStore = useAuthStore();

</script>

<template>
  <div class="app-container">
    <Menu v-if="authStore.isAuthenticated()" />
    <div class="container pt-4 pb-4">
      <RouterView />
    </div>
  </div>
</template>

<style>
#app {
  margin: 0 auto;
  font-weight: normal;
}
.pagination{
  justify-content: center;
}
ul.pagination {
  margin-bottom: 0;
}
</style>
