<script setup>
import { ref } from 'vue';
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";

const props = defineProps(['attribute']);
const emit = defineEmits(['object-attribute-deleted', 'object-attribute-updated']);

const editMode = ref(false);

const attributeCopy = ref({ ...props.attribute });

function deleteObjectAttribute() {
  emit('object-attribute-deleted', { "attribute": props.attribute });
}

function enableEditObjectAttribute() {
  editMode.value = true;
}

function saveObjectAttribute() {
  emit('object-attribute-updated', { "old_attribute": props.attribute, "new_attribute": attributeCopy });
  editMode.value = false;
}

</script>

<template>
  <div class="form-floating input-group mb-3">
    <div class="form-floating">
      <input id="attributeValue" class="form-control" v-model="attributeCopy.value" :disabled="!editMode">
      <label for="attributeValue">value</label>
    </div>
    <div class="form-floating">
      <DistributionLevelSelect :name="`attribute_${attribute.id}.distribution`" v-model="attributeCopy.distribution"
        :disabled="!editMode" />
      <!-- <input id="attributeDistributionLevel" class="form-control" v-model="attributeCopy.distribution" :disabled="!editMode"> -->
        
      <label for="attribute.distribution">distribution</label>
    </div>
    <div class="form-floating">
      <input id="attributeToIDS" class="form-control" v-model="attributeCopy.to_ids" :disabled="!editMode">
      <label for=" attributeToIDS">to_ids</label>
    </div>
    <div class="form-floating">
      <input id="attributeToIDS" class="form-control" v-model="attributeCopy.disable_correlation" :disabled="!editMode">
      <label for=" attributeToIDS">disable_correlation</label>
    </div>
    <div class="form-floating">
      <input id="attributeType" class="form-control" v-model="attributeCopy.template_type" :disabled="!editMode">
      <label for="attributeType">type</label>
    </div>
    <button v-if="!editMode" class="btn btn-outline-primary" type="button" @click="enableEditObjectAttribute">
      <font-awesome-icon icon="fa-solid fa-pen" />
    </button>
    <button v-if="editMode" class="btn btn-outline-primary" type="button" @click="saveObjectAttribute">
      <font-awesome-icon icon="fa-solid fa-floppy-disk" />
    </button>
    <button class="btn btn-danger" type="button" @click="deleteObjectAttribute"><font-awesome-icon
        icon="fa-solid fa-trash" /></button>
  </div>
</template>