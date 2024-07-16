<script setup>
import { ref, watch } from 'vue';
import AddObjectAttributeRow from "@/components/objects/AddObjectAttributeRow.vue";
import ObjectAttributesSelect from "@/components/objects/ObjectAttributesSelect.vue";
import { AttributeSchema } from "@/schemas/attribute";
import { Form, Field, validateObject } from "vee-validate";
import * as Yup from "yup";

const props = defineProps(['template', 'object']);
const object = ref(props.object);
const template = ref(props.template);

const ObjectTemplateSchema = Yup.object().shape({
  attributes: Yup.array()
    .test(
      'at-least-one-required-type',
      `The object must contain at least one attribute with a type matching one of the following: ${template.value.requiredOneOf.join(', ')}`,
      (array) => array && array.some((element) => template.value.requiredOneOf.includes(element.type))
    ),
});
const attribute = ref({
    type: '',
    value: '',
    category: 'category', // TODO: set actual category (need misp_attribute->category map)
    to_ids: false,
    distribution: 0,
    disable_correlation: false
});

let autosuggestAttributeType = true;

function addAttribute(values, { resetForm }) {
    object.value.attributes = [...object.value.attributes, { ...attribute.value }];
    attribute.value.value = '';
    attribute.value.type = ''; // TODO: set actual misp type
    attribute.value.category = 'category'; // TODO: set actual category (need misp_attribute->category map)
    attribute.value.to_ids = false;
    attribute.value.distribution = 0;
    attribute.value.disable_correlation = false;
    autosuggestAttributeType = true;

    resetForm();
}

function handleObjectAttributeDeleted(event) {
    object.value.attributes = object.value.attributes.filter(a => a !== event.attribute);
}

function handleAttributesUpdated(attribute) {
    object.value.attributes = object.value.attributes.filter(a => a.id !== attribute.attribute_id);
}

function handleAttributeTypeChanged(type) {
    attribute.value.type = type;
    autosuggestAttributeType = false;
}

// Watch for changes in the attribute
watch(attribute.value, (newValue, oldValue) => {
    if (!autosuggestAttributeType) {
        return;
    }

    // regex to match ipv4 address
    const ipv4Regex = /\b((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){1,3}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])?\.\b/;
    if (ipv4Regex.test(newValue.value)) {
        attribute.value.type = 'ip';
    }
});

</script>

<template>
    <div class="mt-3 mb-3">
        <span class="fw-bold">{{ template.name }} </span> ({{ template.uuid }})
    </div>
    <AddObjectAttributeRow v-for="attribute in object.attributes" :key="attribute.id" :attribute="attribute"
        @object-attribute-deleted="handleObjectAttributeDeleted" />
    <Form @submit="addAttribute" :validation-schema="AttributeSchema" v-slot="{ errors }">
        <div class="input-group has-validation mb-3">
            <label class="input-group-text" for="attribute.value">value</label>
            <Field class="form-control" id="attribute.value" name="attribute.value" v-model="attribute.value"
                :class="{ 'is-invalid': errors['attribute.value'] }">
            </Field>
            <label class="input-group-text" for="attribute.type">type</label>
            <ObjectAttributesSelect id="attribute.type" name="attribute.type" v-model="attribute.type"
                :errors="errors['attribute.type']" :template="template"
                @attribute-type-changed="handleAttributeTypeChanged" />
            <Field class="form-control" type="hidden" id="attribute.disable_correlation"
                name="attribute.disable_correlation" v-model="attribute.disable_correlation"></Field>

            <Field class="form-control" type="hidden" id="attribute.category" name="attribute.category"
                v-model="attribute.category"></Field>
            <Field class="form-control" type="hidden" id="attribute.distribution" name="attribute.distribution"
                v-model="attribute.distribution"></Field>
            <button type="submit" class="btn btn-outline-primary">Add Attribute</button>
            <div v-for="error in errors" class="invalid-feedback">
                {{ error }}
            </div>
        </div>
    </Form>
</template>