<script setup>
import RoleView from "@/components/roles/RoleView.vue";
const props = defineProps({ id: [String, Number] });
</script>

<template>
  <RoleView :id="props.id" />
</template>
