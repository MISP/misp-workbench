import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/sinks`;

export const useSinksStore = defineStore({
  id: "sinks",
  state: () => ({
    sinks: [],
    sink: null,
    status: {
      loading: false,
      saving: false,
      error: false,
    },
  }),
  actions: {
    async getAll() {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/`)
        .then((sinks) => (this.sinks = sinks))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((sink) => (this.sink = sink))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async create(payload) {
      this.status.saving = true;
      return await fetchWrapper
        .post(`${baseUrl}/`, payload)
        .finally(() => (this.status.saving = false));
    },
    async update(id, payload) {
      this.status.saving = true;
      return await fetchWrapper
        .patch(`${baseUrl}/${id}`, payload)
        .finally(() => (this.status.saving = false));
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    /** Send one synthetic indicator now; resolves to {ok, error}. */
    async test(id) {
      return await fetchWrapper.post(`${baseUrl}/${id}/test`);
    },
  },
});
