import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPEventsStore = defineStore("remote-misp-events", {
  state: () => ({
    remote_events: {},
    remote_event: {},
    remote_event_attributes: {},
    remote_event_objects: {},
    pages: 0,
    page: 0,
    size: 10,
    total: 0,
    status: {
      loading: false,
      loading_attributes: false,
      loading_objects: false,
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
    async get_remote_server_event_attributes(
      server_id,
      event_uuid,
      params = { page: this.page, limit: this.size },
    ) {
      this.status = { loading_attributes: true };
      return await fetchWrapper
        .get(
          `${baseUrl}/${server_id}/events/${event_uuid}/attributes` +
            "/?" +
            new URLSearchParams(params).toString(),
        )
        .then((attributes) => (this.remote_event_attributes = attributes))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading_attributes = false));
    },
    async get_remote_server_event_objects(
      server_id,
      event_uuid,
      params = { page: this.page, limit: this.size },
    ) {
      this.status = { loading_objects: true };
      return await fetchWrapper
        .get(
          `${baseUrl}/${server_id}/events/${event_uuid}/objects` +
            "/?" +
            new URLSearchParams(params).toString(),
        )
        .then((objects) => (this.remote_event_objects = objects))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading_objects = false));
    },
    async pull_remote_misp_event(server_id, event_uuid) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/${server_id}/events/${event_uuid}/pull`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading = false));
    },
  },
});
