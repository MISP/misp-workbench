<script setup>
import { THREAT_LEVEL } from "@/helpers/constants";
defineProps(['threat_level_id']);
</script>

<template>
    <span v-if="threat_level_id === THREAT_LEVEL.HIGH">HIGH</span>
    <span v-if="threat_level_id === THREAT_LEVEL.MEDIUM">MEDIUM</span>
    <span v-if="threat_level_id === THREAT_LEVEL.LOW">LOW</span>
    <span v-if="threat_level_id === THREAT_LEVEL.UNDEFINED">UNDEFINED</span>
</template>