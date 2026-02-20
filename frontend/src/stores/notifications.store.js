import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/notifications`;

export const useNotificationsStore = defineStore("notifications", {
  state: () => ({
    notifications: {},
    notification: {},
    unreadNotifications: 0,
    page_count: 0,
    status: {
      loading: false,
      deleting: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { page: 1, size: 10, read: false }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/?" + new URLSearchParams(params).toString())
        .then(
          (response) => (
            (this.notifications = response),
            (this.page_count = Math.ceil(response.total / params.size))
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getUnreadTotal() {
      fetchWrapper
        .get(`${baseUrl}/?read=false&size=1&page=1`)
        .then((response) => (this.unreadNotifications = response.total))
        .catch((error) => (this.status = { error }));
    },
    async markAsRead(id) {
      this.status = { loading: true };
      fetchWrapper
        .patch(`${baseUrl}/${id}/read`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async unfollow(id) {
      this.status = { loading: true };
      fetchWrapper
        .patch(`${baseUrl}/${id}/unfollow`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async delete(id) {
      this.status = { loading: true };
      return fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
