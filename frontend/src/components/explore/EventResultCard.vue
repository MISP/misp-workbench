<script setup>
import UUID from "@/components/misc/UUID.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import EventActions from "../events/EventActions.vue";
import RetentionBadge from "../events/RetentionBadge.vue";
import EventResultDetails from "./EventResultDetails.vue";
import ExpandToggle from "./ExpandToggle.vue";
import { useCardExpand } from "./useCardExpand";

defineProps(["event", "retentionConfig"]);

const { expanded, onCardClick } = useCardExpand();

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
  <div
    class="card mb-2 event-card"
    :class="{ 'border-primary': expanded }"
    @click="onCardClick"
  >
    <!-- The actions keep their own room, and the uuid and badges wrap
         beside them rather than run under them on a narrow screen. -->
    <div
      class="card-header d-flex align-items-start gap-2 py-2 px-3 bg-body-secondary"
    >
      <div
        class="d-flex align-items-center flex-wrap gap-2 flex-grow-1"
        style="min-width: 0"
      >
        <span class="fw-semibold" style="min-width: 0; max-width: 100%">
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

      <div class="flex-shrink-0">
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

    <div v-if="expanded" class="card-body border-top">
      <EventResultDetails :event="event._source" />
    </div>

    <div class="card-footer d-flex align-items-center gap-2 text-muted small">
      <Timestamp :timestamp="event._source.timestamp" />
      <span v-if="event._score != null" class="badge text-bg-secondary ms-auto">
        score: {{ event._score.toFixed(2) }}
      </span>
      <ExpandToggle
        :class="{ 'ms-auto': event._score == null }"
        :expanded="expanded"
        @toggle="expanded = !expanded"
      />
    </div>
  </div>
</template>

<style scoped>
.event-card {
  cursor: pointer;
}
</style>
