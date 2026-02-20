<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faBellSlash, faTrash } from "@fortawesome/free-solid-svg-icons";
import { useNotificationsStore } from "@/stores";

const notificationsStore = useNotificationsStore();

const props = defineProps(["notification"]);
const emit = defineEmits(["notification-unfollowed", "notification-deleted"]);

function unfollowNotification() {
  notificationsStore.unfollow(props.notification.id).then(() => {
    emit("notification-unfollowed", props.notification.id);
  });
}

function deleteNotification() {
  notificationsStore.delete(props.notification.id).then(() => {
    emit("notification-deleted", props.notification.id);
  });
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
        class="btn btn-outline-primary btn-sm"
        @click="unfollowNotification"
      >
        <FontAwesomeIcon :icon="faBellSlash" />
      </button>
      <button
        type="button"
        class="btn btn-outline-danger btn-sm"
        @click="deleteNotification"
      >
        <FontAwesomeIcon :icon="faTrash" />
      </button>
    </div>
  </div>
</template>
