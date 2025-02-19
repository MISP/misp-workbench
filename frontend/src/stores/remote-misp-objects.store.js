import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPObjectsStore = defineStore("remote-misp-objects", {
  state: () => ({
    remote_event_objects: {},
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
    async get_remote_server_event_objects(
      server_id,
      event_uuid,
      params = { page: this.page, limit: this.size },
    ) {
      this.status.loading_objects = true;
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
  },
});
