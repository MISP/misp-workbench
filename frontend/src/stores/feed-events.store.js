import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/feeds`;

export const useFeedEventsStore = defineStore("feed-events", {
  state: () => ({
    feed_events: [],
    feed_event: null,
    page: 0,
    size: 20,
    total: 0,
    total_filtered: 0,
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get_feed_events(feed_id, params = {}) {
      this.status = { loading: true, error: false };
      this.feed_events = [];
      const queryParams = new URLSearchParams({
        page: this.page,
        limit: this.size,
        ...params,
      });
      return await fetchWrapper
        .get(`${baseUrl}/${feed_id}/explore?${queryParams}`)
        .then((result) => {
          this.feed_events = result.events;
          this.total = result.total;
          this.total_filtered = result.total_filtered;
        })
        .catch((error) => (this.status = { loading: false, error }))
        .finally(() => (this.status.loading = false));
    },
    async get_feed_event(feed_id, event_uuid) {
      this.status = { loading: true, error: false };
      this.feed_event = null;
      return await fetchWrapper
        .get(`${baseUrl}/${feed_id}/explore/${event_uuid}`)
        .then((result) => (this.feed_event = result))
        .catch((error) => (this.status = { loading: false, error }))
        .finally(() => (this.status.loading = false));
    },
    async fetch_feed_event(feed_id, event_uuid) {
      return await fetchWrapper
        .post(`${baseUrl}/${feed_id}/explore/${event_uuid}/fetch`)
        .catch((error) => (this.status = { loading: false, error }));
    },
  },
});
