<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faBellSlash } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["notification"]);
const emit = defineEmits(["notification-unfollowed"]);

function unfollowNotification() {
  emit("notification-unfollowed", props.notification.id);
}
</script>

<style scoped>
.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div class="btn-toolbar float-end" role="toolbar">
    <div
      :class="{ 'btn-group-vertical': $isMobile, 'btn-group me-2': !$isMobile }"
      role="group"
      aria-label="Notification Actions"
    >
      <button
        type="button"
        class="btn btn-outline-primary"
        @click="unfollowNotification"
      >
        <FontAwesomeIcon :icon="faBellSlash" />
      </button>
    </div>
  </div>
</template>
