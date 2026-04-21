import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/api-keys`;

export const useApiKeysStore = defineStore({
  id: "apiKeys",
  state: () => ({
    apiKeys: [],
    status: {
      loading: false,
      creating: false,
      error: null,
    },
  }),
  actions: {
    async getAll() {
      this.status = { loading: true };
      return fetchWrapper
        .get(`${baseUrl}/`)
        .then((keys) => (this.apiKeys = keys))
        .catch((error) => {
          this.status = { error };
          return Promise.reject(error);
        })
        .finally(() => (this.status = { ...this.status, loading: false }));
    },
    async create(payload) {
      this.status = { creating: true };
      return fetchWrapper
        .post(`${baseUrl}/`, payload)
        .catch((error) => Promise.reject(error))
        .finally(() => (this.status = { ...this.status, creating: false }));
    },
    async delete(id) {
      return fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => Promise.reject(error));
    },
  },
});
