import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/exports`;

export const useExportsStore = defineStore({
  id: "exports",
  state: () => ({
    exports: null,
    export: null,
    status: {
      loading: false,
      creating: false,
      error: false,
    },
  }),
  actions: {
    async getAll(params = {}) {
      this.status.loading = true;
      const queryString = new URLSearchParams({
        page: 1,
        size: 50,
        ...params,
      }).toString();
      return fetchWrapper
        .get(`${baseUrl}/?${queryString}`)
        .then((exports) => (this.exports = exports))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((data) => (this.export = data))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async create(payload) {
      this.status.creating = true;
      return await fetchWrapper
        .post(`${baseUrl}/`, payload)
        .finally(() => (this.status.creating = false));
    },
    async updateSchedule(id, payload) {
      return await fetchWrapper.patch(`${baseUrl}/${id}/schedule`, payload);
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    async download(exportItem) {
      const response = await fetchWrapper.downloadAttachment(
        `${baseUrl}/${exportItem.id}/download`,
      );
      if (!response.ok) {
        throw new Error("Export is not ready for download");
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const extension = exportItem.format === "csv" ? "csv" : "json";
      link.download = `${exportItem.name || `export-${exportItem.id}`}.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    },
  },
});
