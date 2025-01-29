<script setup>
import { ref } from "vue";
import ApiError from "@/components/misc/ApiError.vue";
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
import { objectTemplatesHelper } from "@/helpers";

const props = defineProps(["object", "template", "status"]);
const objectTemplateErrors = ref(null);
const apiError = ref(null);

function handleObjectUpdated(event) {
  objectTemplatesHelper
    .validateObject(props.template, props.object)
    .then((validObject) => {
      objectTemplateErrors.value = null;
    })
    .catch((error) => {
      objectTemplateErrors.value = error;
    });
}

function handleObjectAttributeAdded(event) {
  handleObjectUpdated(event);
}

function handleObjectAttributeUpdated(event) {
  handleObjectUpdated(event);
}

function handleObjectAttributeDeleted(event) {
  handleObjectUpdated(event);
}

function updateObject() {
  objectTemplatesHelper
    .validateObject(props.template, props.object)
    .then((validObject) => {
      return objectsStore
        .create(object.value)
        .then((response) => {
          object.value = response.data;
          objectTemplateErrors.value = null;
        })
        .catch((errors) => {
          apiError.value = errors;
        });
    })
    .catch((error) => {
      objectTemplateErrors.value = error;
    });
}
</script>
<template>
  <AddObjectAttributesForm
    :object="object"
    :key="template.uuid"
    :template="template"
    @object-attribute-added="handleObjectAttributeAdded"
    @object-attribute-updated="handleObjectAttributeUpdated"
    @object-attribute-deleted="handleObjectAttributeDeleted"
  />
  <div v-if="objectTemplateErrors" class="w-100 alert alert-danger mt-3 mb-3">
    {{ objectTemplateErrors }}
  </div>
  <div v-if="apiError" class="w-100 alert alert-danger mt-3 mb-3">
    <ApiError :errors="apiError" />
  </div>
  <div class="text-center mt-3">
    <button
      type="submit"
      @submit="updateObject"
      class="btn btn-primary"
      :disabled="status.loading || objectTemplateErrors"
    >
      <span v-show="status.loading">
        <span
          class="spinner-border spinner-border-sm"
          role="status"
          aria-hidden="true"
        ></span>
      </span>
      <span v-show="!status.loading">Save Object</span>
    </button>
  </div>
</template>
