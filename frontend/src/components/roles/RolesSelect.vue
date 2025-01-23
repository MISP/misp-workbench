<script setup>
import { storeToRefs } from "pinia";
import { useRolesStore } from "@/stores";
import { Field } from "vee-validate";

const props = defineProps(["name", "selected", "errors"]);
const emit = defineEmits(["role-updated"]);

const rolesStore = useRolesStore();
const { roles } = storeToRefs(rolesStore);

rolesStore.getAll();

function handleSelectChange(event) {
  emit("role-updated", event.target.value);
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
    <option v-for="role in roles" :value="role.id">{{ role.name }}</option>
  </Field>
</template>
