<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { useRoute } from "vue-router";
import EventUpdate from "@/components/events/EventUpdate.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { router } from "@/router";
const route = useRoute();
const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);
eventsStore.getById(route.params.id);
defineProps(["id"]);
</script>

<template>
  <Spinner v-if="status.loading" />
  <EventUpdate v-if="!status.loading" :event="event" :status="status" />
  <div v-if="status.error" class="text-danger">
    Error loading event: {{ status.error }}
  </div>
</template>
