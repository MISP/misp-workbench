import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tags`;

const CACHE_TTL = 5 * 1000 * 5; // 5 seconds

export const useTagsStore = defineStore("tags", {
  state: () => ({
    tags: [],
    page_count: 0,
    lastFetched: 0,
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { page: 1, size: 100, filter: "", hidden: false }) {
      const hasFilter = params.filter && params.filter.trim() !== "";
      const now = Date.now();
      const isCacheValid = now - this.lastFetched < CACHE_TTL;

      if (!hasFilter && this.tags.length > 0 && isCacheValid) {
        return this.tags;
      }

      try {
        const response = await fetchWrapper.get(
          baseUrl + "/?" + new URLSearchParams(params).toString(),
        );

        // Cache tags if there's no filter
        if (!hasFilter) {
          this.tags = response.items;
          this.lastFetched = Date.now();
        }

        return response;
      } catch (err) {
        this.status.error = true;
        throw err;
      } finally {
        this.status.loading = false;
      }
    },
  },
});
