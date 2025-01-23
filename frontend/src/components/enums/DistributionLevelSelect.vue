<script setup>
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import { Field } from "vee-validate";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["distribution-level-updated"]);

function handleSelectChange(event) {
  emit("distribution-level-updated", event.target.value);
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
    <option v-for="(id, name) in DISTRIBUTION_LEVEL" :value="id" :key="id">
      {{ name }}
    </option>
  </Field>
</template>
