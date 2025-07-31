<script setup>
import { ref, watch } from "vue";
import { router } from "@/router";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import NotificationActions from "@/components/notifications/NotificationActions.vue";
import NotificationText from "@/components/notifications/NotificationText.vue";
import Paginate from "vuejs-paginate-next";
import { useNotificationsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

const searchTerm = ref("");
const showOnlyUnread = ref(false);

const notificationsStore = useNotificationsStore();
const { notifications, status, page_count } = storeToRefs(notificationsStore);
const props = defineProps({ page_size: Number });
function onPageChange(page) {
  notificationsStore.get({
    page: page,
    size: props.page_size,
    filter: searchTerm.value,
  });
}
onPageChange(1);

watch(showOnlyUnread, (newValue) => {
  const params = {
    page: 1,
    size: props.page_size,
    filter: searchTerm.value,
  };
  if (newValue) {
    params.read = false;
  }
  notificationsStore.get({
    ...params,
  });
});

function handleNotificationClick(notification) {
  notificationsStore.markAsRead(notification.id).then(() => {
    notification.read = true;
  });

  if (notification.type.startsWith("organisation.event")) {
    router.push(`/events/${notification.entity_uuid}`);
  }
  if (notification.type.startsWith("organisation.user")) {
    router.push(`/users/${notification.entity_uuid}`);
  }
}

function markAllAsRead() {
  notificationsStore.markAsRead("all").then(() => {
    onPageChange(1);
  });
}

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.extend(relativeTime);
function formatRelativeTime(dateString) {
  const adjustedDate = dayjs.utc(dateString).tz(dayjs.tz.guess());
  return adjustedDate.fromNow();
}
</script>

<template>
  <div class="container">
    <nav class="navbar">
      <div class="container-fluid">
        <div class="navbar-brand">
          <div class="input-group d-flex fs-5 mt-1">
            <div
              class="btn-group"
              role="group"
              aria-label="Filter Notifications"
            >
              <button
                type="button"
                class="btn btn-outline-secondary"
                :class="{ active: !showOnlyUnread }"
                @click="showOnlyUnread = false"
              >
                All
              </button>
              <button
                type="button"
                class="btn btn-outline-secondary"
                :class="{ active: showOnlyUnread }"
                @click="showOnlyUnread = true"
              >
                Unread
              </button>
            </div>
            <div
              class="btn-group ms-4"
              role="group"
              aria-label="Filter Notifications"
            >
              <button
                type="button"
                class="btn btn-outline-primary"
                @click="markAllAsRead()"
              >
                Mark all as read
              </button>
            </div>
          </div>
        </div>
        <form class="d-flex" role="search" @submit.prevent="onPageChange(1)">
          <div class="input-group d-flex">
            <input
              type="text"
              class="form-control"
              v-model="searchTerm"
              placeholder="Search"
            />
            <span
              class="input-group-text"
              @click="onPageChange(1)"
              style="cursor: pointer"
            >
              <FontAwesomeIcon :icon="faMagnifyingGlass" />
            </span>
          </div>
        </form>
      </div>
    </nav>

    <div v-if="status.error" class="text-danger">
      Error loading notifications: {{ status.error }}
    </div>
    <div class="table-responsive-sm">
      <table v-show="!status.loading" class="table border table-hover">
        <tbody>
          <tr
            :key="notification.id"
            v-for="notification in notifications.items"
            :class="{
              'fw-bold': !notification.read,
              'fw-lighter': notification.read,
            }"
          >
            <td
              @click="handleNotificationClick(notification)"
              style="cursor: pointer"
            >
              <NotificationText :notification="notification" />
            </td>
            <td
              @click="handleNotificationClick(notification)"
              style="cursor: pointer"
            >
              {{ notification.type }}
            </td>
            <td
              @click="handleNotificationClick(notification)"
              style="cursor: pointer"
            >
              <span
                data-toggle="tooltip"
                data-placement="top"
                :title="notification.created_at"
              >
                {{ formatRelativeTime(notification.created_at) }}
              </span>
            </td>
            <td>
              <NotificationActions
                :notification="notification"
                @notification-unfollowed="onPageChange(1)"
              />
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="notifications.items?.length === 0" class="text-center">
        <p>No notifications found.</p>
      </div>
      <div class="d-flex justify-content-center mt-3">
        <Paginate
          v-if="page_count > 1"
          :page-count="page_count"
          :click-handler="onPageChange"
        />
      </div>
    </div>
  </div>
  <Spinner v-if="status.loading" />
</template>
