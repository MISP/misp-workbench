import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/hunts`;

export const useHuntsStore = defineStore({
  id: "hunts",
  state: () => ({
    hunts: null,
    hunt: null,
    status: {
      loading: false,
      creating: false,
      updating: false,
      running: false,
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
        .then((hunts) => (this.hunts = hunts))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((hunt) => (this.hunt = hunt))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async create(hunt) {
      this.status.creating = true;
      return await fetchWrapper
        .post(`${baseUrl}/`, hunt)
        .finally(() => (this.status.creating = false));
    },
    async update(id, hunt) {
      this.status.updating = true;
      return await fetchWrapper
        .patch(`${baseUrl}/${id}`, hunt)
        .finally(() => (this.status.updating = false));
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    async run(id) {
      this.status.running = true;
      return await fetchWrapper
        .post(`${baseUrl}/${id}/run`)
        .finally(() => (this.status.running = false));
    },
    async getResults(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/results`);
    },
    async getHistory(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/history`);
    },
  },
});
