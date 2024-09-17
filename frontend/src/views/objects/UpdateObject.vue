<script setup>
import { storeToRefs } from "pinia";
import { useObjectsStore } from "@/stores";
import { useRoute } from "vue-router";
import UpdateObject from "@/components/objects/UpdateObject.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute()
const objectsStore = useObjectsStore();
const { object, status } = storeToRefs(objectsStore);
objectsStore.getById(route.params.id);
defineProps(['id']);
</script>

<template>
    <Spinner v-if="status.loading" />
    <UpdateObject v-if="!status.loading" :object="object" :status="status" />
    <div v-if="status.error" class="text-danger">
        Error loading object: {{ status.error }}
    </div>
</template>