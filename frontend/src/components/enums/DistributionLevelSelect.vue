<script setup>
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
defineProps(['modelValue']);
defineEmits(['update:modelValue'])
</script>

<template>
    <select class="form-select" :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)">
        <option v-for="(id, name) in DISTRIBUTION_LEVEL" :value="id">{{ name }}</option>
    </select>
</template>