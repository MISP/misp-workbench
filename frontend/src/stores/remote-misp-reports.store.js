import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useRemoteMISPReportsStore = defineStore("remote-misp-reports", {
  state: () => ({
    remote_event_reports: {},
    status: {
      loading: false,
      updating: false,
      creating: false,
      error: false,
    },
  }),
  actions: {
    async get_remote_server_event_reports(server_id, event_id) {
      this.status.loading_reports = true;
      return await fetchWrapper
        .get(`${baseUrl}/${server_id}/events/${event_id}/reports`)
        .then((reports) => (this.remote_event_reports = reports))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.loading_reports = false));
    },
  },
});
