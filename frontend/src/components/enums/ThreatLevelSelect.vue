<script setup>
import { THREAT_LEVEL } from "@/helpers/constants";
defineProps(['selected']);
</script>

<template>
    <select class="form-select" v-model="selected">
        <option v-for="(id, name) in THREAT_LEVEL" :value="id">{{ name }}</option>
    </select>
</template>