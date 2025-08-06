import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/settings/user`;

export const useUserSettingsStore = defineStore("userSettings", {
  state: () => ({
    userSettings: null,
    userSetting: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getAll(force = false) {
      if (this.userSettings && !force) return this.userSettings;

      this.status.loading = true;
      this.status.error = null;

      try {
        const response = await fetchWrapper.get(baseUrl);
        this.userSettings = response;
        return response;
      } catch (error) {
        this.status.error = error;
        throw error;
      } finally {
        this.status.loading = false;
      }
    },
    async getByNamespace(namespace) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${namespace}`)
        .then((userSetting) => (this.userSetting = userSetting))
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
