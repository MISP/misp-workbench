<script setup>
import { DISTRIBUTION_LEVEL } from "@/helpers/constants";
defineProps(['selected']);
</script>

<template>
    <select class="form-select" v-model="selected">
        <option v-for="(id, name) in DISTRIBUTION_LEVEL" :value="id">{{ name }}</option>
    </select>
</template>