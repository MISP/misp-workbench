<script setup>
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
import { objectTemplatesHelper } from "@/helpers";

const props = defineProps(["object", "template", "status"]);

function handleAttributesUpdated() {
    objectTemplatesHelper.validateObject(template.value, object)
        .then((validObject) => {
            objectTemplateErrors.value = null;
        })
        .catch((error) => {
            objectTemplateErrors.value = error;
        });
}
</script>
<template>
    <AddObjectAttributesForm :object="object" :key="template.uuid" :template="template"
        @object-attribute-added="handleAttributesUpdated" @object-attribute-deleted="handleAttributesUpdated" />
</template>
