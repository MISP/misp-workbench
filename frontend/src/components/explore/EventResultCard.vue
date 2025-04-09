<script setup>
import UUID from "@/components/misc/UUID.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
defineProps(["event"]);
</script>

<template>
  <div class="card mb-2">
    <div class="card-header">
      <a :href="`/events/${event._source.id}`">
        {{ event._source.info }}
      </a>
    </div>
    <div class="card-body">
      <h6 class="card-subtitle mb-2 text-muted">
        <UUID :uuid="event._source.uuid" />
      </h6>
      <p class="card-text text-truncate">
        <TagsIndex :tags="event._source.tags" />
      </p>
      <p class="card-text"></p>
    </div>
    <div class="card-footer text-muted">
      <Timestamp :timestamp="event._source.timestamp" />
    </div>
  </div>
</template>
