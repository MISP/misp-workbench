import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tags`;

export const useTagsStore = defineStore({
  id: "tags",
  state: () => ({
    tags: {},
    page_count: 0,
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { page: 1, size: 100 }) {
      this.status = { loading: true };
      return fetchWrapper.get(
        baseUrl + "/?" + new URLSearchParams(params).toString(),
      );
    },
  },
});
