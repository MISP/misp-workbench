import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/settings/user`;

export const useUserSettingsStore = defineStore("userSettings", {
  state: () => ({
    userSettings: {},
    userSetting: {},
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
          this.userSettings = response;
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
