<script setup>
import { Field } from "vee-validate";

let props = defineProps(['name', 'selected', 'errors']);
const emit = defineEmits(['to_ids-updated']);

function handleSelectChange(event) {
    emit('to_ids-updated', event.target.value);
}
</script>

<template>
    <Field class="form-control" :name="name" :class="{ 'is-invalid': errors }" as="select" @change="handleSelectChange"
        :value="props.selected">
        <option value="true">true</option>
        <option valie="false">false</option>
    </Field>
</template>