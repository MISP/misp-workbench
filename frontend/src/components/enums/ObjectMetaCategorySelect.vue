<script setup>
import { OBJECT_META_CATEGORIES } from "@/helpers/constants";
import { Field } from "vee-validate";
import { toRef } from "vue";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["object-meta-category-updated"]);

function handleSelectChange(event) {
  emit("object-meta-category-updated", event.target.value);
}
</script>

<template>
  <Field
    class="form-control"
    :name="name"
    :class="{ 'is-invalid': errors }"
    as="select"
    @change="handleSelectChange"
    :value="props.selected"
  >
    <option
      v-for="(_, name) in OBJECT_META_CATEGORIES"
      :value="name"
      :key="name"
    >
      {{ name }}
    </option>
  </Field>
</template>
