import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/indicators`;

export const useIndicatorsStore = defineStore({
  id: "indicators",
  state: () => ({
    page: { total: 0, page: 1, size: 50, items: [] },
    indicatorsStatus: null,
    status: { loading: false, error: false },
  }),
  actions: {
    /** One page of consolidated indicators (one per type + value). */
    async search(params = {}) {
      this.status.loading = true;
      this.status.error = false;
      const query = new URLSearchParams(
        Object.entries(params).filter(
          ([, v]) => v !== null && v !== undefined && v !== "",
        ),
      );
      return fetchWrapper
        .get(`${baseUrl}?${query}`)
        .then((page) => (this.page = page))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getStatus() {
      return fetchWrapper
        .get(`${baseUrl}/status`)
        .then((status) => (this.indicatorsStatus = status))
        .catch(() => (this.indicatorsStatus = null));
    },
  },
});
