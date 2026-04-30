import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tech-lab/reactor`;

export const useReactorStore = defineStore({
  id: "reactor",
  state: () => ({
    scripts: null,
    script: null,
    runs: null,
    status: {
      loading: false,
      creating: false,
      updating: false,
      testing: false,
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
        .get(`${baseUrl}/scripts/?${queryString}`)
        .then((scripts) => (this.scripts = scripts))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/scripts/${id}`)
        .then((script) => (this.script = script))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getSource(id) {
      return fetchWrapper.get(`${baseUrl}/scripts/${id}/source`);
    },
    async create(payload) {
      this.status.creating = true;
      return await fetchWrapper
        .post(`${baseUrl}/scripts/`, payload)
        .finally(() => (this.status.creating = false));
    },
    async update(id, payload) {
      this.status.updating = true;
      return await fetchWrapper
        .patch(`${baseUrl}/scripts/${id}`, payload)
        .finally(() => (this.status.updating = false));
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/scripts/${id}`);
    },
    async getRuns(id, params = {}) {
      const queryString = new URLSearchParams({
        page: 1,
        size: 25,
        ...params,
      }).toString();
      return fetchWrapper
        .get(`${baseUrl}/scripts/${id}/runs?${queryString}`)
        .then((runs) => (this.runs = runs));
    },
    async getRunLog(runId) {
      return fetchWrapper.get(`${baseUrl}/runs/${runId}/log`);
    },
    async test(id, payload = {}) {
      this.status.testing = true;
      return await fetchWrapper
        .post(`${baseUrl}/scripts/${id}/test`, { payload })
        .finally(() => (this.status.testing = false));
    },
  },
});
