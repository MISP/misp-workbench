import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPEventsStore = defineStore("remote-misp-events", {
  state: () => ({
    remote_events: {},
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
      serverId,
      params = { page: this.page, limit: this.size },
    ) {
      this.status = { loading: true };
      return await fetchWrapper
        .get(
          `${baseUrl}/${serverId}/events-index` +
            "/?" +
            new URLSearchParams(params).toString(),
        )
        .then((events) => (this.remote_events = events))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading = false));
    },
    async pull_remote_misp_event(serverId, uuid) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/${serverId}/events/${uuid}/pull`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading = false));
    },
  },
});
