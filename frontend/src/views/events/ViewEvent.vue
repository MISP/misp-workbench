<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["id", "tab"]);
</script>

<template>
  <EventView :event_uuid="id" :tab="tab" :key="id" />
</template>
