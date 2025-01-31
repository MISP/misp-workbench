<script setup>
import { ref } from "vue";
import DistributionLevelSelect from "@/components/enums/DistributionLevelSelect.vue";
import ToIDSSelect from "@/components/enums/ToIDSSelect.vue";
import DisableCorrelationSelect from "@/components/enums/DisableCorrelationSelect.vue";
import ObjectTemplateAttributeTypeSelect from "@/components/objects/ObjectTemplateAttributeTypeSelect.vue";
import ObjectTemplateAttributeObjectRelationSelect from "@/components/objects/ObjectTemplateAttributeObjectRelationSelect.vue";
import { getAttributeTypeValidationSchema } from "@/schemas/attribute";

const props = defineProps(["attribute", "template"]);
const emit = defineEmits([
  "object-attribute-deleted",
  "object-attribute-updated",
]);

const editMode = ref(false);

const attributeCopy = ref({ ...props.attribute });
const errors = ref(null);

const AttributeTypeSchema = ref(getAttributeTypeValidationSchema("text"));
const selectedTemplateAttribute = ref({});

function deleteObjectAttribute() {
  emit("object-attribute-deleted", { attribute: props.attribute });
}

function enableEditObjectAttribute() {
  editMode.value = true;
}

function saveObjectAttribute() {
  const attributeFormObject = { attribute: attributeCopy.value };
  AttributeTypeSchema.value
    .validate(attributeFormObject)
    .then(() => {
      errors.value = null;
      editMode.value = false;
      emit("object-attribute-updated", {
        old_attribute: props.attribute,
        new_attribute: attributeCopy,
      });
    })
    .catch((error) => {
      errors.value = error;
    });
}

function handleAttributeObjecRelationChanged(relation) {
  props.template.attributes.forEach((templateAttribute) => {
    if (templateAttribute.name === relation) {
      selectedTemplateAttribute.value = templateAttribute;
      attributeCopy.value.type =
        selectedTemplateAttribute.value["misp_attribute"];
    }
  });
  AttributeTypeSchema.value = getAttributeTypeValidationSchema(
    attributeCopy.value.type,
  );
}

function handleAttributeTypeChanged(type) {
  attributeCopy.value.type = type;
  AttributeTypeSchema.value = getAttributeTypeValidationSchema(
    attributeCopy.value.type,
  );
}
</script>

<template>
  <div class="form-floating input-group mb-3">
    <div class="form-floating">
      <input
        :name="`attribute_${attribute.id}.value`"
        class="form-control"
        v-model="attributeCopy.value"
        :disabled="!editMode"
      />
      <label>value</label>
    </div>
    <div class="form-floating">
      <DistributionLevelSelect
        :name="`attribute_${attribute.id}.distribution`"
        v-model="attributeCopy.distribution"
        :disabled="!editMode"
      />
      <label for="attribute.distribution">distribution</label>
    </div>
    <div class="form-floating">
      <ToIDSSelect
        :name="`attribute_${attribute.id}.to_ids`"
        v-model="attributeCopy.to_ids"
        :disabled="!editMode"
      />
      <label>to_ids</label>
    </div>
    <div class="form-floating">
      <DisableCorrelationSelect
        :name="`attribute_${attribute.id}.disable_correlation`"
        v-model="attributeCopy.disable_correlation"
        :disabled="!editMode"
      />
      <label>disable_correlation</label>
    </div>
    <div class="form-floating">
      <ObjectTemplateAttributeObjectRelationSelect
        :name="`attribute_${attribute.id}.object_relation`"
        :template="template"
        :selected="attributeCopy.object_relation"
        v-model="attributeCopy.object_relation"
        @attribute-template-object-relation-changed="
          handleAttributeObjecRelationChanged($event, attribute)
        "
        :disabled="!editMode"
      />
      <label>relation</label>
    </div>
    <div class="form-floating">
      <ObjectTemplateAttributeTypeSelect
        :name="`attribute_${attribute.id}.type`"
        :template="template"
        :selected="attributeCopy.type"
        v-model="attributeCopy.type"
        @attribute-template-type-changed="
          handleAttributeTypeChanged($event, attribute)
        "
        :disabled="!editMode"
      />
      <label>type</label>
    </div>
    <button
      v-if="!editMode"
      class="btn btn-outline-primary"
      type="button"
      @click="enableEditObjectAttribute"
    >
      <font-awesome-icon icon="fa-solid fa-pen" />
    </button>
    <button
      v-if="editMode"
      class="btn btn-outline-primary"
      type="button"
      @click="saveObjectAttribute"
    >
      <font-awesome-icon icon="fa-solid fa-floppy-disk" />
    </button>
    <button
      class="btn btn-outline-danger"
      type="button"
      @click="deleteObjectAttribute"
    >
      <font-awesome-icon icon="fa-solid fa-trash" />
    </button>
    <div v-if="errors" class="w-100 alert alert-danger mt-3 mb-3">
      <span>{{ errors }}</span>
    </div>
  </div>
</template>
