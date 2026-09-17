<script setup>
import ServoEditor from "@/components/servos/ServoEditor.vue";

defineProps({
  id: { type: [String, Number], required: true },
});
</script>

<template>
  <ServoEditor mode="edit" :servo-id="id" />
</template>
