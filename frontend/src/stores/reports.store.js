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
      creating: false,
      error: false,
    },
  }),
  actions: {
    async getReportsByEventId(event_uuid) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${event_uuid}`)
        .then((reports) => (this.reports = reports))
        .catch((error) => (this.report = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async create(event_uuid, report) {
      this.status = { creating: true };
      return await fetchWrapper
        .post(`${baseUrl}/${event_uuid}`, report)
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status = { creating: false }));
    },
    async update(report_uuid, report) {
      this.status = { loading: true };
      return await fetchWrapper
        .put(`${baseUrl}/${report_uuid}`, report)
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status = { loading: false }));
    },
    async delete(report_uuid) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${report_uuid}`)
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
