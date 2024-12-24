<script setup>
import { storeToRefs } from "pinia";
import { useGalaxiesStore } from "@/stores";
import { useRoute } from "vue-router";
import GalaxyView from "@/components/galaxies/GalaxyView.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute()
const galaxiesStore = useGalaxiesStore();
const { galaxy, status } = storeToRefs(galaxiesStore);
galaxiesStore.getById(route.params.id);
defineProps(['id']);
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
    <GalaxyView v-show="!status.loading" :galaxy="galaxy" :status="status" />
    <div v-if="status.error" class="text-danger">
        Error loading galaxy: {{ status.error }}
    </div>
</template>