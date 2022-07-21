<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { RouterLink, useRoute } from "vue-router";
import EventView from "@/components/events/EventView.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute() 
const eventsStore = useEventsStore();
const { event } = storeToRefs(eventsStore);
eventsStore.getById(route.params.id);
defineProps(['id']);
</script>

<style>
.card{
    text-align: left;
}
.btn-group{
    display: inline-block;
}
.organisation-name{
    font-size: 1.2rem;
}
</style>

<template>
    <Spinner v-if="event.loading" />
    <EventView v-if="!event.loading" :event="event"/>
    <div v-if="event.error" class="text-danger">
        Error loading event: {{ event.error }}
    </div>
</template>