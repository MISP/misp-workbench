<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import { useObjectsStore } from "@/stores";
import { useRoute } from "vue-router";
import EditObject from "@/components/objects/EditObject.vue";
import Spinner from "@/components/misc/Spinner.vue";

defineProps(["id"]);

const route = useRoute();
const objectsStore = useObjectsStore();
const { object, objectTemplates, status } = storeToRefs(objectsStore);

objectsStore.getById(route.params.id);
objectsStore.getObjectTemplates();

const isLoaded = computed(() => {
  return (
    object.value !== null &&
    objectTemplates.value.length > 0 &&
    !status.value.loading
  );
});
</script>

<template>
  <Spinner v-if="!isLoaded" />
  <EditObject
    v-else
    :object="object"
    :template="objectsStore.getObjectTemplateByUuid(object.template_uuid)"
    :status="status"
  />
  <div v-if="status.error" class="text-danger">
    Error loading object: {{ status.error }}
  </div>
</template>
