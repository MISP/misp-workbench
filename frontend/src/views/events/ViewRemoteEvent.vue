<script setup>
import EventViewRemote from "@/components/events/EventViewRemote.vue";

defineProps(["server_id", "event_uuid"]);
</script>

<template>
  <EventViewRemote :server_id="server_id" :event_uuid="event_uuid" />
</template>
