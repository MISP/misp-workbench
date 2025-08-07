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
    default:
      return props.notification?.title || "unknown notification";
  }
});
</script>

<template>
  <div v-if="notification">
    <div v-if="notification.type.startsWith('organisation.event')">
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
        {{ notification.title }} in
        <code>{{ notification.payload.event_title }}</code> event
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.attribute_type
        }}</span>
        {{ notification.payload.attribute_value }}
      </div>
    </div>
    <div v-else-if="notification.type.startsWith('event.object')">
      <div class="text-muted small">
        {{ notification.title }} in
        <code>{{ notification.payload.event_title }}</code> event
      </div>
      <div>
        <span class="badge bg-info text-dark me-2">{{
          notification.payload.object_template
        }}</span>
      </div>
    </div>
    <div v-else>{{ title }}</div>
  </div>
</template>
