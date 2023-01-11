<script setup>
import { storeToRefs } from 'pinia'
import { useRolesStore } from "@/stores";
import { Field } from "vee-validate";
import { toRef } from "vue"

let props = defineProps(['name', 'selected', 'errors']);
const selected = toRef(props, 'selected')

const rolesStore = useRolesStore();
const { roles } = storeToRefs(rolesStore);

rolesStore.getAll();

</script>

<template>
    <Field class="form-control" :name="name" v-model="selected" :class="{ 'is-invalid': errors }" as="select">
        <option v-for="role in roles" :value="role.id">{{ role.name }}</option>
    </Field>
</template>