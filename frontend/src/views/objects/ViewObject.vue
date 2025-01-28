<script setup>
import { storeToRefs } from "pinia";
import { useObjectsStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import ViewObject from "@/components/objects/ViewObject.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const objectStore = useObjectsStore();
const { object, status } = storeToRefs(objectStore);
objectStore.getById(route.params.id);
defineProps(["id"]);
</script>

<style>
.card {
  text-align: left;
}

.btn-group {
  display: inline-block;
}
</style>

<template>
  <Spinner v-if="status.loading" />
  <ViewObject v-show="!status.loading" :object="object" :status="status" />
  <div v-if="status.error" class="text-danger">
    Error loading object: {{ status.error }}
  </div>
</template>
