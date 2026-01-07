<script setup>
import { ref, watch } from "vue";
import { ATTRIBUTE_CATEGORIES, ATTRIBUTE_TYPES } from "@/helpers/constants";
import { Field } from "vee-validate";

const props = defineProps(["name", "category", "selected", "errors"]);
const emit = defineEmits(["attribute-type-updated"]);

const types = ref([]);

function resolveTypes(category) {
  if (ATTRIBUTE_CATEGORIES[category] === undefined) {
    return ATTRIBUTE_TYPES;
  }
  return ATTRIBUTE_CATEGORIES[category].types;
}

types.value = resolveTypes(props.category);

watch(
  () => props.category,
  (newCategory) => {
    types.value = resolveTypes(newCategory);
  },
);

function handleInput(event) {
  const value = event.target.value;

  if (types.value.includes(value)) {
    emit("attribute-type-updated", value);
  }
}
</script>

<template>
  <Field
    class="form-control"
    :name="name"
    list="attributeTypeOptions"
    :class="{ 'is-invalid': errors }"
    placeholder="Search attribute type…"
    :value="selected"
    @input="handleInput"
  />

  <datalist id="attributeTypeOptions">
    <option v-for="type in types" :key="type" :value="type" />
  </datalist>
</template>
