<script setup>
import EventViewRemote from "@/components/events/EventViewRemote.vue";

defineProps(["feed_id", "event_uuid"]);
</script>

<template>
  <EventViewRemote :feed_id="feed_id" :event_uuid="event_uuid" />
</template>
