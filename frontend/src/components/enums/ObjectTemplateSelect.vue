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
    <Field class="form-control" list="objectTemplateOptions" id="objectTemplatesSelect" :name="name" :class="{ 'is-invalid': errors }"  @change="handleSelectChange"
    placeholder="Type to search..." :value="props.selected.uuid"></Field>
    <datalist id="objectTemplateOptions" >
        <option v-for="template in objectTemplates" :value="template.uuid" :uuid="template.uuid">{{ template.name }}</option>
    </datalist>
</template>