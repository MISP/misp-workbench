<script setup>
import AddObjectAttributesForm from "@/components/objects/AddObjectAttributesForm.vue";
const props = defineProps(["object", "template", "status"]);

function getObjectTemplateSchema(template) {
  return Yup.object().shape({
    attributes: Yup.array().test(
      "at-least-one-required-type",
      `The object must contain at least one attribute with a type matching one of the following: ${template.requiredOneOf.join(
        ", ",
      )}`,
      (attributes) =>
        attributes &&
        attributes.some((attribute) =>
          template.requiredOneOf.includes(attribute.template_type),
        ),
    ),
  });
}

const validateObject = (template, object) => {
  return new Promise((resolve, reject) => {
    const schema = getObjectTemplateSchema(template);
    ObjectSchema.concat(schema)
      .validate(object)
      .then((validObject) => {
        objectTemplateErrors.value = null;
        resolve(validObject);
      })
      .catch((error) => {
        objectTemplateErrors.value = error;
        reject(error);
      });
  });
};

function handleAttributesUpdated() {
  validateObject(template.value, object)
    .then((validObject) => {
      objectTemplateErrors.value = null;
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
    @object-attribute-added="handleAttributesUpdated"
    @object-attribute-deleted="handleAttributesUpdated"
  />
</template>
