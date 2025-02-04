<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { useRoute } from "vue-router";
import OrganisationView from "@/components/organisations/OrganisationView.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const organisationsStore = useOrganisationsStore();
const { organisation, status } = storeToRefs(organisationsStore);
organisationsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <OrganisationView v-show="!status.loading" :organisation="organisation" />
  <div v-if="status.error" class="text-danger">
    Error loading organisation: {{ status.error }}
  </div>
</template>
