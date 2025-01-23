<script setup>
import { THREAT_LEVEL } from "@/helpers/constants";
import { Field } from "vee-validate";
import { toRef } from "vue";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["threat-level-updated"]);

function handleSelectChange(event) {
  emit("threat-level-updated", event.target.value);
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
    <option v-for="(id, name) in THREAT_LEVEL" :value="id" :key="id">
      {{ name }}
    </option>
  </Field>
</template>
