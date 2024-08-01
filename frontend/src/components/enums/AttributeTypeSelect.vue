<script setup>
import { ref } from "vue"
import { ATTRIBUTE_CATEGORIES, ATTRIBUTE_TYPES } from "@/helpers/constants";
import { Field } from "vee-validate";

let props = defineProps(['name', 'category', 'selected', 'errors']);
const emit = defineEmits(['attribute-type-updated']);

function handleSelectChange(event) {
    emit('attribute-type-updated', event.target.value);
}

const types = ref([]);

if (ATTRIBUTE_CATEGORIES[props.category] === undefined) {
    types.value = ATTRIBUTE_TYPES;
} else {
    types.value = ATTRIBUTE_CATEGORIES[props.category]['types'];
}

</script>

<template>
    <Field class="form-control" :name="name" :class="{ 'is-invalid': errors }" as="select" @change="handleSelectChange"
        :value="props.selected">
        <option v-for="(type) in types" :value="type">{{ type }}</option>
    </Field>
</template>