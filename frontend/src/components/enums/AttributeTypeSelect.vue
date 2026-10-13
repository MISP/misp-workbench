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

// The field reads `selected` once, when it mounts: follow later changes too
// (a type detected from the value as it is typed), without remounting it.
const field = ref(null);
watch(
  () => props.selected,
  (selected) => {
    field.value?.handleChange(selected ?? "", false);
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
    ref="field"
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
