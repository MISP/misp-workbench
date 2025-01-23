<script setup>
import { ANALYSIS_LEVEL } from "@/helpers/constants";
defineProps(["analysis_level_id"]);
</script>

<template>
  <span v-if="analysis_level_id === ANALYSIS_LEVEL.INITIAL">INITIAL</span>
  <span v-if="analysis_level_id === ANALYSIS_LEVEL.ONGOING">ONGOING</span>
  <span v-if="analysis_level_id === ANALYSIS_LEVEL.COMPLETE">COMPLETE</span>
</template>
