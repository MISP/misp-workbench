import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPEventsStore = defineStore("remote-misp-events", {
  state: () => ({
    remote_events: {},
    remote_event: {},
    pages: 0,
    page: 0,
    size: 10,
    total: 0,
    status: {
      loading: false,
      updating: false,
      creating: false,
      error: false,
    },
  }),
  actions: {
    async get_remote_server_events_index(
      server_id,
      params = { page: this.page, limit: this.size },
    ) {
      this.status = { loading: true };
      this.remote_events = {};
      return await fetchWrapper
        .get(
          `${baseUrl}/${server_id}/events-index` +
            "/?" +
            new URLSearchParams(params).toString(),
        )
        .then((events) => (this.remote_events = events))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading = false));
    },
    async pull_remote_misp_event(server_id, event_uuid) {
      return await fetchWrapper
        .post(`${baseUrl}/${server_id}/events/${event_uuid}/pull`)
        .catch((error) => (this.status = { error }));
    },
  },
});
