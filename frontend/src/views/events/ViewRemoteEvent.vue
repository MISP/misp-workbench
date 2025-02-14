<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["server_id", "event_uuid"]);
</script>

<style>
.card {
  text-align: left;
}

.btn-group {
  display: inline-block;
}

.organisation-name {
  font-size: 1.2rem;
}
</style>

<template>
  <EventView :server_id="server_id" :event_uuid="event_uuid" />
</template>
