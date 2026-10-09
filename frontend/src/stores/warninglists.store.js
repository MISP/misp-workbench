import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/warninglists`;

export const useWarninglistsStore = defineStore({
  id: "warninglists",
  state: () => ({
    warninglists: [],
    status: { loading: false, updating: false, error: false },
  }),
  actions: {
    async getAll() {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/`)
        .then((lists) => (this.warninglists = lists))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async setEnabled(id, enabled) {
      return await fetchWrapper.patch(`${baseUrl}/${id}`, { enabled });
    },
    /** Queue a load of new and updated lists from the bundled submodule. */
    async update() {
      this.status.updating = true;
      return await fetchWrapper
        .post(`${baseUrl}/update`)
        .finally(() => (this.status.updating = false));
    },
    /** {value: [list names]} for the values that hit an enabled list. */
    async check(values, type = null) {
      return await fetchWrapper.post(`${baseUrl}/check`, { values, type });
    },
  },
});
