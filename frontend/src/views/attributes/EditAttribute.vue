<script setup>
import { storeToRefs } from "pinia";
import { useAttributesStore } from "@/stores";
import { useRoute } from "vue-router";
import AttributeUpdate from "@/components/attributes/AttributeUpdate.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute();
const attributesStore = useAttributesStore();
const { attribute, status } = storeToRefs(attributesStore);
attributesStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <AttributeUpdate
    v-if="!status.loading"
    :attribute="attribute"
    :status="status"
  />
  <div v-if="status.error" class="text-danger">
    Error loading attribute: {{ status.error }}
  </div>
</template>
