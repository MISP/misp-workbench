<script setup>
import { ANALYSIS_LEVEL } from "@/helpers/constants";
import { Field } from "vee-validate";
import { toRef } from "vue";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["analysis-level-updated"]);

function handleSelectChange(event) {
  emit("analysis-level-updated", event.target.value);
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
    <option v-for="(id, name) in ANALYSIS_LEVEL" :value="id" :key="id">
      {{ name }}
    </option>
  </Field>
</template>
