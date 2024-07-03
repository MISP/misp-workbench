<script setup>
import { Field } from "vee-validate";

const props = defineProps(['name', 'selected', 'errors', 'template']);
const emit = defineEmits(['attribute-type-changed']);

function handleSelectChange(event) {
    emit('attribute-type-changed', event.target.value);
}

</script>

<template>
    <Field class="form-control form-select" :name="name" :class="{ 'is-invalid': errors }" as="select" @change="handleSelectChange"
        :value="props.selected">
        <option v-for="attribute in template.attributes" :value="attribute.name">{{ attribute.name }}</option>
    </Field>
</template>