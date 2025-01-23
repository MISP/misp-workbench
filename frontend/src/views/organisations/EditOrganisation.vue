<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { useRoute } from "vue-router";
import OrganisationUpdate from "@/components/organisations/OrganisationUpdate.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute();
const organisationsStore = useOrganisationsStore();
const { organisation, status } = storeToRefs(organisationsStore);
organisationsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <OrganisationUpdate
    v-if="!status.loading"
    :organisation="organisation"
    :status="status"
  />
  <div v-if="status.error" class="text-danger">
    Error loading organisation: {{ status.error }}
  </div>
</template>
