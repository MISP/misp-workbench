<script setup>
defineProps({ notification: Object });
</script>

<template>
  <div v-if="notification.type.startsWith('organisation.event')">
    <div class="text-muted small">{{ notification.title }}</div>
    <div>{{ notification.payload.event_name }}</div>
  </div>
  <div v-else>{{ notification.title }}</div>
</template>
