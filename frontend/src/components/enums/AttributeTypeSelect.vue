<script setup>
import { ATTRIBUTE_CATEGORIES } from "@/helpers/constants";
import { Field } from "vee-validate";

let props = defineProps(['name', 'category', 'selected', 'errors']);
const emit = defineEmits(['attribute-type-updated']);

function handleSelectChange(event) {
    emit('attribute-type-updated', event.target.value);
}
</script>

<template>
    <Field class="form-control" :name="name" :class="{ 'is-invalid': errors }" as="select" @change="handleSelectChange"
        :value="props.selected">
        <option v-for="(type) in ATTRIBUTE_CATEGORIES[category]['types']" :value="type">{{ type }}</option>
    </Field>
</template>