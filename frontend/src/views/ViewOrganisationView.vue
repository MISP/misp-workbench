<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import OrganisationView from "@/components/organisations/OrganisationView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute()
const organisationsStore = useOrganisationsStore();
const { organisation } = storeToRefs(organisationsStore);
organisationsStore.getById(route.params.id);
defineProps(['id']);
</script>

<style>
.card {
    text-align: left;
}

.btn-group {
    display: inline-block;
}

.organisation-name {
    font-size: 1.2rem;
}
</style>

<template>
    <Spinner v-if="organisation.loading" />
    <OrganisationView v-if="!organisation.loading" :organisation="organisation" />
    <div v-if="organisation.error" class="text-danger">
        Error loading organisation: {{ organisation.error }}
    </div>
</template>