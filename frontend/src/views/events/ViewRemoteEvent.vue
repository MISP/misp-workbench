<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["server_id", "event_uuid"]);
</script>

<template>
  <EventView :server_id="server_id" :event_uuid="event_uuid" />
</template>
