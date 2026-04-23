import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/admin/audit-logs`;

export const useAuditLogsStore = defineStore({
  id: "auditLogs",
  state: () => ({
    auditLogs: { items: [], total: 0, page: 1, size: 25, pages: 0 },
    status: {
      loading: false,
      error: null,
    },
  }),
  actions: {
    async getAll(params = { page: 1, size: 25 }) {
      this.status = { loading: true };
      const query = {};
      for (const [k, v] of Object.entries(params)) {
        if (v !== null && v !== undefined && v !== "") query[k] = v;
      }
      return fetchWrapper
        .get(`${baseUrl}/?${new URLSearchParams(query).toString()}`)
        .then((response) => (this.auditLogs = response))
        .catch((error) => {
          this.status = { error };
          return Promise.reject(error);
        })
        .finally(() => (this.status = { ...this.status, loading: false }));
    },
  },
});
