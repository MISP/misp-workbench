<script setup>
import { ref } from 'vue';
import AddObjectAttributeRow from "@/components/objects/AddObjectAttributeRow.vue";
import ObjectTemplateAttributeTypeSelect from "@/components/objects/ObjectTemplateAttributeTypeSelect.vue";
import ObjectAttributeValueInput from "@/components/objects/ObjectAttributeValueInput.vue";
import { AttributeSchema, getAttributeTypeValidationSchema } from "@/schemas/attribute";
import { Form, Field } from "vee-validate";
import * as Yup from "yup";

const props = defineProps(['template', 'object']);
const emit = defineEmits(['object-attribute-added', 'object-attribute-deleted']);
const object = ref(props.object);
const template = ref(props.template);

const AttributeTypeSchema = ref(getAttributeTypeValidationSchema('text'));

const attributeErrors = ref(null);

const attribute = ref({
    event_id: object.value.event_id,
    value: '',
    category: 'category', // TODO: set actual category (need misp_attribute->category map)
    to_ids: false,
    distribution: 0,
    disable_correlation: false
});

const selectedTemplateAttribute = ref({});

function addAttribute(values, { resetForm }) {
    validateAttributeValue(values, AttributeTypeSchema.value)
        .then((validAttribute) => {
            object.value.attributes = [...object.value.attributes, { ...attribute.value }];

            // reset defaults
            attribute.value.value = '';
            attribute.value.category = 'category'; // TODO: set actual category (need misp_attribute->category map)
            attribute.value.to_ids = false;
            attribute.value.distribution = 0;
            attribute.value.disable_correlation = false;

            emit('object-attribute-added', { "attribute": attribute.value });

            console.log(object.value.attributes);

            attributeErrors.value = null;
            resetForm();
        })
        .catch((error) => {
            attributeErrors.value = error;
        });
}

function handleObjectAttributeDeleted(event) {
    object.value.attributes = object.value.attributes.filter(a => a !== event.attribute);
    emit('object-attribute-deleted', { "attribute": event.attribute });
}

function handleAttributesUpdated(attribute) {
    object.value.attributes = object.value.attributes.filter(a => a.id !== attribute.attribute_id);
}

function handleAttributeTypeChanged(type) {
    attribute.value.template_type = type;
    template.value.attributes.forEach((templateAttribute) => {
        if (templateAttribute.name === type) {
            selectedTemplateAttribute.value = templateAttribute;
            attribute.value.type = selectedTemplateAttribute.value['misp_attribute'];
        }
    });

    AttributeTypeSchema.value = getAttributeTypeValidationSchema(type);
}

const validateAttributeValue = (object, schema) => {
    return new Promise((resolve, reject) => {
        schema.validate(object)
            .then((validAttribute) => {
                resolve(validAttribute);
            })
            .catch((error) => {
                reject(error);
            });
    });
};


function handleAttributeValueChanged(value) {
    attribute.value.value = value;
}

</script>

<template>
    <div>
        <div class="mt-3 mb-3">
            <p>
                <button class="btn btn-primary" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapseTemplateInfo">
                    <span class="fw-bold">{{ template.name }} </span> ({{ template.uuid }})
                </button>
            </p>
            <div class="collapse" id="collapseTemplateInfo">
                <div class="card card-body">
                    <div><span class="badge bg-secondary flex">{{ template.meta_category }}</span>
                    </div>
                    <div>
                        <span>{{ template.description }}</span>
                    </div>
                    <span class="fw-bold">requires one of:</span>
                    <ul>
                        <li v-for="attribute in template.requiredOneOf">{{ attribute }}</li>
                    </ul>
                </div>
            </div>
        </div>
        <AddObjectAttributeRow v-for="attribute in object.attributes" :key="attribute.id" :attribute="attribute"
            @object-attribute-deleted="handleObjectAttributeDeleted" />
        <Form @submit="addAttribute" :validation-schema="AttributeSchema" v-slot="{ errors }">
            <div class="input-group has-validation mb-3">
                <label class="input-group-text" for="attribute.value">value</label>
                <ObjectAttributeValueInput id="attribute.value" name="attribute.value"
                    :attribyte_type="selectedTemplateAttribute" v-model="attribute.value"
                    :errors="errors['attribute.value']" @attribute-value-changed="handleAttributeValueChanged" />
                <label class="input-group-text" for="attribute.type">type</label>
                <ObjectTemplateAttributeTypeSelect id="attribute.template_type" name="attribute.template_type"
                    v-model="attribute.template_type" :errors="errors['attribute.type']" :template="template"
                    @attribute-template-type-changed="handleAttributeTypeChanged" />
                <Field class="form-control" type="hidden" id="attribute.disable_correlation"
                    name="attribute.disable_correlation" v-model="attribute.disable_correlation"></Field>
                <Field class="form-control" type="hidden" id="attribute.event_id" name="attribute.event_id"
                    v-model="attribute.event_id"></Field>
                <Field class="form-control" type="hidden" id="attribute.category" name="attribute.category"
                    v-model="attribute.category"></Field>
                <Field class="form-control" type="hidden" id="attribute.distribution" name="attribute.distribution"
                    v-model="attribute.distribution"></Field>
                <Field class="form-control" type="hidden" id="attribute.type" name="attribute.type"
                    v-model="attribute.type"></Field>
                <label v-if="attribute.type" class="input-group-text" for="attribute.description"><font-awesome-icon
                        icon="fa-solid fa-circle-info" class="btn-success" data-bs-toggle="tooltip"
                        data-bs-placement="top" :title="selectedTemplateAttribute.description" /></label>
                <button type="submit" class="btn btn-outline-primary">Add
                    Attribute</button>
                <div v-if="attributeErrors" class="w-100 alert alert-danger mt-3 mb-3">
                    <span>{{ attributeErrors }}</span>
                </div>
            </div>
        </Form>
    </div>
</template>