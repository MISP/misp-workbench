<script setup>
import { OBJECT_META_CATEGORIES } from "@/helpers/constants";
import { Field } from "vee-validate";
import { useObjectsStore } from "@/stores";
import { storeToRefs } from 'pinia'

let props = defineProps(['name', 'meta_category', 'selected', 'errors']);
const emit = defineEmits(['object-template-updated']);

const objectsStore = useObjectsStore();
const { objectTemplates } = storeToRefs(objectsStore);

objectsStore.getObjectTemplates();

function handleSelectChange(event) {
    emit('object-template-updated', event.target.value);
}
</script>

<template>
    <Field class="form-control" :name="name" :class="{ 'is-invalid': errors }" as="select" @change="handleSelectChange"
        :value="props.selected">
        <option v-for="(template) in objectTemplates" :value="template.uuid">{{ template.name }}
        </option>
    </Field>
</template>