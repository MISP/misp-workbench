<script setup>
import RoleEdit from "@/components/roles/RoleEdit.vue";
const props = defineProps({ id: [String, Number] });
</script>

<template>
  <RoleEdit :id="props.id" />
</template>
