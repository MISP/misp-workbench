<script setup>
import { storeToRefs } from "pinia";
import { useTaxonomiesStore } from "@/stores";
import { useRoute } from "vue-router";
import TaxonomyView from "@/components/taxonomies/TaxonomyView.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const taxonomiesStore = useTaxonomiesStore();
const { taxonomy, status } = storeToRefs(taxonomiesStore);
taxonomiesStore.getById(route.params.id);
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
  <TaxonomyView
    v-show="!status.loading"
    :taxonomy="taxonomy"
    :status="status"
  />
  <div v-if="status.error" class="text-danger">
    Error loading taxonomy: {{ status.error }}
  </div>
</template>
