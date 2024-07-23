<script setup>
import { ref, watch } from 'vue';
import AddObjectAttributeRow from "@/components/objects/AddObjectAttributeRow.vue";
import ObjectTemplateAttributesSelect from "@/components/objects/ObjectTemplateAttributesSelect.vue";
import ObjectAttributeValueInput from "@/components/objects/ObjectAttributeValueInput.vue";
import { AttributeSchema } from "@/schemas/attribute";
import { Form, Field, validateObject } from "vee-validate";

const props = defineProps(['template', 'object']);
const emit = defineEmits(['object-attribute-added', 'object-attribute-deleted']);
const object = ref(props.object);
const template = ref(props.template);

const attribute = ref({
    event_id: object.value.event_id,
    value: '',
    type: '',
    category: 'category', // TODO: set actual category (need misp_attribute->category map)
    to_ids: false,
    distribution: 0,
    disable_correlation: false
});

const selectedTemplateAttribute = ref({});

let autosuggestAttributeType = true;

function addAttribute(values, { resetForm }) {
    object.value.attributes = [...object.value.attributes, { ...attribute.value }];
    attribute.value.value = '';
    attribute.value.type = selectedTemplateAttribute.value['misp-attribute'];
    attribute.value.category = 'category'; // TODO: set actual category (need misp_attribute->category map)
    attribute.value.to_ids = false;
    attribute.value.distribution = 0;
    attribute.value.disable_correlation = false;
    autosuggestAttributeType = true;

    emit('object-attribute-added', { "attribute": attribute.value });

    resetForm();
}

function handleObjectAttributeDeleted(event) {
    object.value.attributes = object.value.attributes.filter(a => a !== event.attribute);
    emit('object-attribute-deleted', { "attribute": event.attribute });
}

function handleAttributesUpdated(attribute) {
    object.value.attributes = object.value.attributes.filter(a => a.id !== attribute.attribute_id);
}

function handleAttributeTypeChanged(type) {
    attribute.value.type = type;
    template.value.attributes.forEach((templateAttribute) => {
        if (templateAttribute.name === type) {
            selectedTemplateAttribute.value = templateAttribute;
        }
    });
    autosuggestAttributeType = false;
}


function handleAttributeValueChanged(value) {
    attribute.value.value = value;
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
            <ObjectTemplateAttributesSelect id="attribute.type" name="attribute.type" v-model="attribute.type"
                :errors="errors['attribute.type']" :template="template"
                @attribute-type-changed="handleAttributeTypeChanged" />
            <Field class="form-control" type="hidden" id="attribute.disable_correlation"
                name="attribute.disable_correlation" v-model="attribute.disable_correlation"></Field>
            <Field class="form-control" type="hidden" id="attribute.event_id" name="attribute.event_id"
                v-model="attribute.event_id"></Field>
            <Field class="form-control" type="hidden" id="attribute.category" name="attribute.category"
                v-model="attribute.category"></Field>
            <Field class="form-control" type="hidden" id="attribute.distribution" name="attribute.distribution"
                v-model="attribute.distribution"></Field>
            <label v-if="attribute.type" class="input-group-text" for="attribute.description"><font-awesome-icon
            icon="fa-solid fa-circle-info" class="btn-success" data-bs-toggle="tooltip" data-bs-placement="top"
            :title="selectedTemplateAttribute.description" /></label>
            <button type="submit" class="btn btn-outline-primary">Add Attribute</button>
            <div v-for="error in errors" class="invalid-feedback">
                {{ error }}
            </div>
        </div>
    </Form>
</template>