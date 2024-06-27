<script setup>

import ObjectAttributesSelect from "@/components/objects/ObjectAttributesSelect.vue";


const props = defineProps(['attribute']);
const emit = defineEmits(['object-attribute-deleted']);

function deleteObjectAttribute() {
  emit('object-attribute-deleted', { "attribute": props.attribute });
}

</script>

<template>
  <div class="form-floating input-group mb-3">
    <div class="form-floating w-50">
      <input id="attributeValue" class="form-control" :value="attribute.value" disabled>
      <label for="attributeValue">value</label>
    </div>
    <div class="form-floating">
      <input id="attributeDistributionLevel" class="form-control" :value="attribute.distribution" disabled>
      <label for="attributeDistributionLevel">distribution</label>
    </div>
    <div class="form-floating">
      <input id="attributeToIDS" class="form-control" :value="attribute.to_ids" disabled>
      <label for="attributeToIDS">to_ids</label>
    </div>
    <div class="form-floating">
      <input id="attributeToIDS" class="form-control" :value="!attribute.disable_correlation" disabled>
      <label for="attributeToIDS">correlate</label>
    </div>
    <div class="form-floating">
      <input id="attributeType" class="form-control" :value="attribute.type" disabled>
      <label for="attributeType">type</label>
    </div>
    <button class="btn btn-outline-primary" type="button"><font-awesome-icon icon="fa-solid fa-pen" /></button>
    <button class="btn btn-outline-danger" type="button" @click="deleteObjectAttribute"><font-awesome-icon
        icon="fa-solid fa-trash" /></button>
  </div>
</template>