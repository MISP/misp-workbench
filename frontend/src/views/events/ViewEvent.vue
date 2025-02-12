<script setup>
import EventView from "@/components/events/EventView.vue";

defineProps(["id"]);
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
  <EventView :event_id="id" />
</template>
