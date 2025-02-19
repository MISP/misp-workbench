import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPAttributesStore = defineStore(
  "remote-misp-attributes",
  {
    state: () => ({
      remote_event_attributes: {},
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
      async get_remote_server_event_attributes(
        server_id,
        event_uuid,
        params = { page: this.page, limit: this.size },
      ) {
        this.status = { loading: true };
        return await fetchWrapper
          .get(
            `${baseUrl}/${server_id}/events/${event_uuid}/attributes` +
              "/?" +
              new URLSearchParams(params).toString(),
          )
          .then(
            (attributes) =>
              (this.remote_event_attributes = attributes.Attribute),
          )
          .catch((error) => (this.status.error = error))
          .finally(() => (this.status.loading = false));
      },
    },
  },
);
