<script setup>
defineProps({ notification: Object });
</script>

<template>
  <div v-if="notification.type.startsWith('organisation.event')">
    <div class="text-muted small">
      {{ notification.title }} from
      <code>{{ notification.payload.organisation_name }}</code>
    </div>
    <div>{{ notification.payload.event_name }}</div>
  </div>
  <div v-else-if="notification.type.startsWith('event.attribute')">
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
  <div v-else>{{ notification.title }}</div>
</template>
