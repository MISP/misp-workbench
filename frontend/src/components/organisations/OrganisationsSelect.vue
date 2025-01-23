<script setup>
import { storeToRefs } from "pinia";
import { useOrganisationsStore } from "@/stores";
import { Field } from "vee-validate";
import { toRef } from "vue";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["organisation-updated"]);

const organisationsStore = useOrganisationsStore();
const { organisations } = storeToRefs(organisationsStore);

organisationsStore.getAll();

function handleSelectChange(event) {
  emit("organisation-updated", event.target.value);
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
    <option v-for="org in organisations" :value="org.id" :key="org.id">
      {{ org.name }}
    </option>
  </Field>
</template>
