<script setup>
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
import { Field } from "vee-validate";
import {toRef} from "vue"
let props = defineProps(['name', 'selected', 'errors']);
const selected = toRef(props,'selected')
</script>

<template>
    <Field class="form-control" :name="name" v-model="selected" :class="{ 'is-invalid': errors }" as="select">
        <option v-for="(id, name) in DISTRIBUTION_LEVEL" :value="id">{{ name }}</option>
    </Field>
</template>