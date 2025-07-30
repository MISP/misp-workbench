<script setup>
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import Paginate from "vuejs-paginate-next";
import { useNotificationsStore } from "@/stores";

const notificationsStore = useNotificationsStore();
const { notifications, status, page_count } = storeToRefs(notificationsStore);
const props = defineProps({ page_size: Number });
function onPageChange(page) {
  notificationsStore.get({
    page: page,
    size: props.page_size,
  });
}
onPageChange(1);

function handleNotificationClick(notification) {
  notificationsStore.markAsRead(notification.id).then(() => {
    // Optionally, you can refresh the notifications list or handle UI updates here
    notification.read = true;
  });
}
</script>

<template>
  <Spinner v-if="status.loading" />
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
          @click="handleNotificationClick(notification)"
          style="cursor: pointer"
        >
          <td>
            {{ notification.title }}
          </td>
          <td>
            {{ notification.type }}
          </td>
          <td>
            {{ notification.created_at }}
          </td>
        </tr>
      </tbody>
    </table>
    <div class="d-flex justify-content-center mt-3">
      <Paginate
        v-if="page_count > 1"
        :page-count="page_count"
        :click-handler="onPageChange"
      />
    </div>
  </div>
  <Spinner v-if="status.loading" />
</template>
