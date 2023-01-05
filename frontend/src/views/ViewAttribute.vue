<script setup>
import { storeToRefs } from "pinia";
import { useAttributesStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import AttributeView from "@/components/attributes/AttributeView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute()
const attributeStore = useAttributesStore();
const { attribute, status } = storeToRefs(attributeStore);
attributeStore.getById(route.params.id);
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
    <AttributeView v-if="!status.loading" :attribute="attribute" :status="status" />
    <div v-if="status.error" class="text-danger">
        Error loading attribute: {{ status.error }}
    </div>
</template>