<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["uuid"]);
</script>

<template>
  <EventView :event_uuid="uuid" :key="uuid" />
</template>
