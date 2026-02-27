<script setup>
import { computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faBellSlash, faTrash, faEye } from "@fortawesome/free-solid-svg-icons";
import { useNotificationsStore } from "@/stores";

const notificationsStore = useNotificationsStore();

const props = defineProps(["notification"]);
const emit = defineEmits(["notification-unfollowed", "notification-deleted"]);

const entityRoute = computed(() => {
  const { entity_type, payload } = props.notification;
  if (entity_type === "hunt") return `/hunts/${payload.hunt_id}`;
  if (entity_type === "event") return `/events/${payload.event_uuid}`;
  if (entity_type === "attribute" || entity_type === "object")
    return `/events/${payload.event_uuid}`;
  return null;
});

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
      <RouterLink
        v-if="entityRoute"
        :to="entityRoute"
        class="btn btn-outline-primary btn-sm"
        title="View"
      >
        <FontAwesomeIcon :icon="faEye" />
      </RouterLink>
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
