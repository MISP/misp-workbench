<script setup>
import EventViewRemote from "@/components/events/EventViewRemote.vue";

defineProps(["server_id", "uuid"]);
</script>

<template>
  <EventViewRemote :server_id="server_id" :event_uuid="uuid" />
</template>
