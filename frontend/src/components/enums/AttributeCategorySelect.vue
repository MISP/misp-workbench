<script setup>
import { ATTRIBUTE_CATEGORIES } from "@/helpers/constants";
import { Field } from "vee-validate";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["attribute-category-updated"]);

function handleSelectChange(event) {
  emit("attribute-category-updated", event.target.value);
}
</script>

<template>
  <Field
    class="form-select"
    :name="name"
    :class="{ 'is-invalid': errors }"
    as="select"
    @change="handleSelectChange"
    :value="props.selected"
  >
    <option v-for="(_, name) in ATTRIBUTE_CATEGORIES" :value="name" :key="name">
      {{ name }}
    </option>
  </Field>
</template>
