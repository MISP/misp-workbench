<script setup>
import UUID from "@/components/misc/UUID.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import EventActions from "../events/EventActions.vue";
defineProps(["event"]);
</script>

<template>
  <div class="card mb-2">
    <div class="card-header position-relative py-2 px-3 bg-body-secondary">
      <div class="d-flex align-items-center gap-2">
        <span class="fw-semibold">
          <UUID :uuid="event._source.uuid" :copy="true" />
        </span>
      </div>

      <div class="position-absolute bottom-0 end-0 me-2 mb-1">
        <EventActions :event_uuid="event._source.uuid" />
      </div>
    </div>
    <div class="card-body">
      <h6 class="card-subtitle mb-2">
        {{ event._source.info }}
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
