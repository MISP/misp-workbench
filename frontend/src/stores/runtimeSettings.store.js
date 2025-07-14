import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/settings/runtime`;

export const useRuntimeSettingsStore = defineStore("settings", {
  state: () => ({
    settings: {},
    setting: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getAll() {
      this.status = { loading: true };
      return fetchWrapper
        .get(baseUrl)
        .then((response) => {
          this.settings = response;
        })
        .catch((error) => {
          this.status = { error };
        })
        .finally(() => {
          this.status = { loading: false };
        });
    },
    async getByNamespace(namespace) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${namespace}`)
        .then((setting) => (this.setting = setting))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async delete(namespace) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${namespace}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async update(namespace, data) {
      this.status = { updating: true };
      return await fetchWrapper
        .post(`${baseUrl}/${namespace}`, data)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.updating = false));
    },
  },
});
