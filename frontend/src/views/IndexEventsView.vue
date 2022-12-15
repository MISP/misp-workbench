<script setup>
import EventsIndex from "@/components/events/EventsIndex.vue";
import AddEventButton from "@/components/events/AddEventButton.vue";
</script>

<template>
    <AddEventButton />
    <EventsIndex :page_size="10" />
</template>