<script setup>
import UUID from "@/components/misc/UUID.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import EventActions from "../events/EventActions.vue";
import RetentionBadge from "../events/RetentionBadge.vue";

defineProps(["event", "retentionConfig"]);

const threatLevelMap = {
  1: { label: "high", cls: "bg-danger" },
  2: { label: "medium", cls: "bg-warning text-dark" },
  3: { label: "low", cls: "bg-success" },
  4: { label: "undefined", cls: "bg-secondary" },
};

const analysisMap = {
  0: { label: "initial", cls: "bg-secondary" },
  1: { label: "ongoing", cls: "bg-info text-dark" },
  2: { label: "completed", cls: "bg-success" },
};
</script>

<template>
  <div class="card mb-2">
    <div class="card-header position-relative py-2 px-3 bg-body-secondary">
      <div class="d-flex align-items-center gap-2">
        <span class="fw-semibold">
          <UUID :uuid="event._source.uuid" :copy="true" />
        </span>
        <span
          v-if="!event._source.published"
          class="badge bg-warning text-dark"
          title="Not published"
          >unpublished</span
        >
        <RetentionBadge
          v-if="retentionConfig"
          :event-timestamp="event._source.timestamp"
          :retention-config="retentionConfig"
          :tags="event._source.tags || []"
        />
      </div>

      <div class="position-absolute bottom-0 end-0 me-2 mb-1">
        <EventActions :event_uuid="event._source.uuid" />
      </div>
    </div>

    <div class="card-body">
      <div class="alert alert-info h6 mt-2" role="alert">
        {{ event._source.info }}
      </div>
      <div class="d-flex align-items-center gap-2 mb-2 flex-wrap">
        <span
          v-if="threatLevelMap[event._source.threat_level]"
          class="badge"
          :class="threatLevelMap[event._source.threat_level].cls"
          >threat_level:{{
            threatLevelMap[event._source.threat_level].label
          }}</span
        >

        <span
          v-if="analysisMap[event._source.analysis] != null"
          class="badge"
          :class="analysisMap[event._source.analysis].cls"
          >analysis:{{ analysisMap[event._source.analysis].label }}</span
        >

        <span v-if="event._source.organisation?.name" class="text-muted small">
          organisation: {{ event._source.organisation.name }}
        </span>

        <span class="text-muted small ms-auto">
          <template v-if="event._source.attribute_count">
            {{ event._source.attribute_count }} attrs
          </template>
          <template v-if="event._source.object_count">
            · {{ event._source.object_count }} objects
          </template>
        </span>
      </div>

      <p class="card-text text-truncate">
        <TagsIndex :tags="event._source.tags" />
      </p>
    </div>

    <div class="card-footer d-flex justify-content-between text-muted small">
      <Timestamp :timestamp="event._source.timestamp" />
      <span v-if="event._score != null" class="badge text-bg-secondary">
        score: {{ event._score.toFixed(2) }}
      </span>
    </div>
  </div>
</template>
