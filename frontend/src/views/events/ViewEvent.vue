<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["id"]);
</script>

<template>
  <EventView :event_id="id" />
</template>
