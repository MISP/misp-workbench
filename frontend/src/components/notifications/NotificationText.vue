<script setup>
import { computed } from "vue";

const props = defineProps({ notification: Object });

const title = computed(() => {
  switch (props.notification?.type) {
    case "organisation.event.created":
      return `new event created`;
    case "organisation.event.updated":
      return `event updated`;
    case "organisation.event.deleted":
      return `event deleted`;
    case "event.attribute.created":
      return `attribute created`;
    case "event.attribute.updated":
      return `attribute updated`;
    case "event.attribute.deleted":
      return `attribute deleted`;
    case "event.object.created":
      return `object created`;
    case "event.object.updated":
      return `object updated`;
    case "event.object.deleted":
      return `object deleted`;
    case "event.updated":
      return `event updated`;
    case "event.deleted":
      return `event deleted`;
    case "attribute.updated":
      return `attribute updated`;
    case "attribute.deleted":
      return `attribute deleted`;
    case "attribute.sighting.created":
      return `attribute sighted`;
    case "attribute.correlation.created":
      return `attribute correlation found`;
    case "object.updated":
      return `object updated`;
    case "object.deleted":
      return `object deleted`;
    case "hunt.result.changed":
      return `hunt matches`;
    default:
      return props.notification?.title || "unknown notification";
  }
});

const deltaMatches = computed(() => {
  if (props.notification?.type !== "hunt.result.changed") return null;
  const total = props.notification.payload.total || 0;
  const previousTotal = props.notification.payload.previous_total || 0;
  return total - previousTotal;
});
</script>

<template>
  <div v-if="notification">
    <div v-if="notification.type.startsWith('attribute.sighting.created')">
      <div class="text-muted small">
        {{ title }} by <code>{{ notification.payload.organisation }}</code>
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.attribute_type
        }}</span>
        {{ notification.payload.sighting_value }}
      </div>
    </div>
    <div
      v-else-if="notification.type.startsWith('attribute.correlation.created')"
    >
      <div class="text-muted small">
        {{ title }}
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.target_attribute_type
        }}</span>
        {{ notification.payload.target_attribute_value }}
      </div>
    </div>
    <div v-else-if="notification.type.startsWith('organisation.event')">
      <div class="text-muted small">
        {{ title }} from
        <code>{{ notification.payload.organisation_name }}</code>
      </div>
      <div>{{ notification.payload.event_name }}</div>
    </div>
    <div
      v-else-if="
        notification.type.startsWith('event.updated') ||
        notification.type.startsWith('event.deleted')
      "
    >
      {{ title }}
      <code>{{ notification.payload.event_name }}</code>
    </div>
    <div
      v-else-if="
        notification.type.startsWith('event.attribute') ||
        notification.type.startsWith('attribute')
      "
    >
      <div class="text-muted small">
        {{ title }} in <code>{{ notification.payload.event_title }}</code> event
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.attribute_type
        }}</span>
        {{ notification.payload.attribute_value }}
      </div>
    </div>
    <div
      v-else-if="
        notification.type.startsWith('event.object') ||
        notification.type.startsWith('object')
      "
    >
      <div class="text-muted small">
        {{ title }} in <code>{{ notification.payload.event_title }}</code> event
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.object_name
        }}</span>
      </div>
    </div>
    <div v-if="notification.type.startsWith('hunt.result.changed')">
      <div class="text-muted small">
        {{ title }} for <code>{{ notification.payload.hunt_name }}</code>
      </div>
      <div>
        <span class="text-dark me-2">
          <span v-if="deltaMatches > 0" class="badge bg-danger text-dark me-2"
            >{{ deltaMatches }} new match{{
              deltaMatches > 1 ? "es" : ""
            }}</span
          >
          <span
            v-if="deltaMatches <= 0"
            class="badge bg-secondary text-dark me-2"
          >
            {{ deltaMatches }}
            lost match{{ deltaMatches < -1 ? "es" : "" }}</span
          >
        </span>
      </div>
    </div>
    <div v-else>{{ title }}</div>
  </div>
</template>
