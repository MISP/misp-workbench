import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/reports`;

export const useReportsStore = defineStore({
  id: "reports",
  state: () => ({
    reports: {},
    report: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getReportsByEventId(event_id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${event_id}`)
        .then((reports) => (this.reports = reports))
        .catch((error) => (this.report = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
