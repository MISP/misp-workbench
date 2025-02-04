<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { useRoute } from "vue-router";
import EventView from "@/components/events/EventView.vue";
import Spinner from "@/components/misc/Spinner.vue";
const route = useRoute();
const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);

eventsStore.getById(route.params.id);
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
  <Spinner v-if="status.loading" />
  <EventView
    v-show="!status.loading"
    :event_id="id"
    :event="event"
    :status="status"
  />
  <div v-if="status.error" class="text-danger">
    Error loading event: {{ status.error }}
  </div>
</template>
