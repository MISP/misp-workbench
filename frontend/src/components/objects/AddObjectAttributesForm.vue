<script setup>
import { ref } from "vue";
import AddOrEditObjectAttributeRow from "@/components/objects/AddOrEditObjectAttributeRow.vue";
import ObjectTemplateAttributeTypeSelect from "@/components/objects/ObjectTemplateAttributeTypeSelect.vue";
import ObjectTemplateAttributeObjectRelationSelect from "@/components/objects/ObjectTemplateAttributeObjectRelationSelect.vue";
import ObjectAttributeValueInput from "@/components/objects/ObjectAttributeValueInput.vue";
import {
  AttributeSchema,
  getAttributeTypeValidationSchema,
} from "@/schemas/attribute";
import UUID from "@/components/misc/UUID.vue";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const props = defineProps(["template", "object"]);
const emit = defineEmits([
  "object-attribute-added",
  "object-attribute-deleted",
  "object-attribute-updated",
]);
const object = ref(props.object);
const template = ref(props.template);

const AttributeTypeSchema = ref(getAttributeTypeValidationSchema("text"));

const attributeErrors = ref(null);

const newAttribute = ref({
  event_id: object.value.event_id,
  value: "",
  category: "Other",
  to_ids: false,
  distribution: 0,
  disable_correlation: false,
});

const selectedTemplateAttribute = ref({});

function addAttribute(values, { resetForm }) {
  validateAttributeValue(values, AttributeTypeSchema.value)
    .then((validAttribute) => {
      object.value.attributes = [
        ...object.value.attributes,
        { ...newAttribute.value },
      ];
      emit("object-attribute-added", { attribute: { ...newAttribute.value } });

      // reset defaults
      newAttribute.value.value = "";
      newAttribute.value.category = "Other";
      newAttribute.value.to_ids = false;
      newAttribute.value.distribution = 0;
      newAttribute.value.disable_correlation = true;

      attributeErrors.value = null;
      resetForm();
    })
    .catch((error) => {
      attributeErrors.value = error;
    });
}

function handleObjectAttributeDeleted(event) {
  object.value.attributes = object.value.attributes.filter(
    (attribute) => attribute !== event.attribute,
  );
  emit("object-attribute-deleted", { attribute: event.attribute });
}

function handleObjectAttributeUpdated(event) {
  // replace old attribute with new attribute
  object.value.attributes = object.value.attributes.map((attribute) => {
    if (attribute === event.old_attribute) {
      return event.new_attribute.value;
    }
    return attribute;
  });
  emit("object-attribute-updated", { attribute: event.new_attribute });
}

function handleAttributeObjectRelationChanged(object_relation) {
  template.value.attributes.forEach((templateAttribute) => {
    if (templateAttribute.name === object_relation) {
      selectedTemplateAttribute.value = templateAttribute;
      newAttribute.value.type =
        selectedTemplateAttribute.value["misp_attribute"];
      newAttribute.value.disable_correlation =
        selectedTemplateAttribute.value["disable_correlation"];
    }
  });

  AttributeTypeSchema.value = getAttributeTypeValidationSchema(
    newAttribute.value.type,
  );
}

function handleAttributeTypeChanged(type) {
  AttributeTypeSchema.value = getAttributeTypeValidationSchema(
    newAttribute.value.type,
  );
}

const validateAttributeValue = (object, schema) => {
  return new Promise((resolve, reject) => {
    schema
      .validate(object)
      .then((validAttribute) => {
        resolve(validAttribute);
      })
      .catch((error) => {
        reject(error);
      });
  });
};

function handleAttributeValueChanged(value) {
  newAttribute.value.value = value;
}
</script>

<template>
  <div>
    <div class="mt-3 mb-3">
      <div class="card card-body">
        <div>
          <span class="fw-bold">{{ template.name }} </span>
          <span class="badge bg-info flex">v{{ template.version }}</span>
        </div>
        <div>
          <UUID :uuid="template.uuid" />
        </div>
        <div>
          <span class="badge bg-secondary flex">{{
            template.meta_category
          }}</span>
        </div>
        <div>
          <span>{{ template.description }}</span>
        </div>
        <span class="fw-bold">requires one of:</span>
        <ul>
          <li v-for="attribute in template.requiredOneOf" :key="attribute.id">
            {{ attribute }}
          </li>
        </ul>
      </div>
    </div>
    <Form
      @submit="addAttribute"
      :validation-schema="AttributeSchema"
      v-slot="{ errors }"
    >
      <div class="input-group has-validation mb-3">
        <label class="input-group-text" for="attribute.value">value</label>
        <ObjectAttributeValueInput
          id="attribute.value"
          name="attribute.value"
          :attribute_type="selectedTemplateAttribute"
          v-model="newAttribute.value"
          :errors="errors['newAttribute.value']"
          @attribute-value-changed="handleAttributeValueChanged"
        />
        <label class="input-group-text" for="attribute.object_relation"
          >relation</label
        >
        <ObjectTemplateAttributeObjectRelationSelect
          id="attribute.object_relation"
          name="attribute.object_relation"
          v-model="newAttribute.object_relation"
          :errors="errors['newAttribute.object_relation']"
          :template="template"
          @attribute-template-object-relation-changed="
            handleAttributeObjectRelationChanged
          "
        />
        <label class="input-group-text" for="attribute.type">type</label>
        <ObjectTemplateAttributeTypeSelect
          id="attribute.type"
          name="attribute.type"
          v-model="newAttribute.type"
          :errors="errors['newAttribute.type']"
          :template="template"
          @attribute-template-type-changed="handleAttributeTypeChanged"
        />
        <Field
          class="form-control"
          type="hidden"
          id="attribute.disable_correlation"
          name="attribute.disable_correlation"
          v-model="newAttribute.disable_correlation"
        ></Field>
        <Field
          class="form-control"
          type="hidden"
          id="attribute.event_id"
          name="attribute.event_id"
          v-model="newAttribute.event_id"
        ></Field>
        <Field
          class="form-control"
          type="hidden"
          id="attribute.category"
          name="attribute.category"
          v-model="newAttribute.category"
        ></Field>
        <Field
          class="form-control"
          type="hidden"
          id="attribute.distribution"
          name="attribute.distribution"
          v-model="newAttribute.distribution"
        ></Field>
        <Field
          class="form-control"
          type="hidden"
          id="attribute.type"
          name="attribute.type"
          v-model="newAttribute.type"
        >
        </Field>
        <label
          v-if="newAttribute.type"
          class="input-group-text"
          for="attribute.description"
          ><font-awesome-icon
            icon="fa-solid fa-circle-info"
            class="btn-success"
            data-bs-toggle="tooltip"
            data-bs-placement="top"
            :title="selectedTemplateAttribute.description"
        /></label>
        <button type="submit" class="btn btn-outline-primary">
          Add Attribute
        </button>
        <div v-if="attributeErrors" class="w-100 alert alert-danger mt-3 mb-3">
          <span>{{ attributeErrors }}</span>
        </div>
      </div>
    </Form>
    <AddOrEditObjectAttributeRow
      v-for="attribute in object.attributes.filter(
        (attribute) => !attribute.deleted,
      )"
      :key="attribute.id"
      :attribute="attribute"
      :template="template"
      @object-attribute-deleted="handleObjectAttributeDeleted"
      @object-attribute-updated="handleObjectAttributeUpdated"
    />
  </div>
</template>
