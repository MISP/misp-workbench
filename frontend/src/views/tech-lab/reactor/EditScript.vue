<script setup>
import ScriptEditor from "@/components/reactor/ScriptEditor.vue";

defineProps({ id: { type: [String, Number], required: true } });
</script>

<template>
  <ScriptEditor mode="edit" :scriptId="id" />
</template>
