import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/local-warninglists`;

function queryString(params) {
  return new URLSearchParams(
    Object.entries(params).filter(
      ([, v]) => v !== null && v !== undefined && v !== "",
    ),
  ).toString();
}

// Organisations' own warninglists: yours (every organisation's, for admins).
export const useLocalWarninglistsStore = defineStore({
  id: "localWarninglists",
  state: () => ({
    lists: [],
    loaded: false,
    status: { loading: false, error: false },
  }),
  getters: {
    /** id -> list, to name the lists an indicator hits. */
    byId: (state) => Object.fromEntries(state.lists.map((l) => [l.id, l])),
  },
  actions: {
    async getAll() {
      this.status.loading = true;
      this.status.error = false;
      return fetchWrapper
        .get(baseUrl)
        .then((lists) => {
          this.lists = lists;
          this.loaded = true;
        })
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    /** Load once, for pages that only name lists. */
    async ensureLoaded() {
      if (!this.loaded && !this.status.loading) await this.getAll();
    },
    /** The hosts lists may sync from, as an admin allowed them. */
    async sources() {
      return (await fetchWrapper.get(`${baseUrl}/sources`)).hosts;
    },
    async get(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}`);
    },
    async create(list) {
      return await fetchWrapper.post(baseUrl, list);
    },
    async update(id, patch) {
      return await fetchWrapper.patch(`${baseUrl}/${id}`, patch);
    },
    async remove(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    async entries(id, params = {}) {
      return await fetchWrapper.get(
        `${baseUrl}/${id}/entries?${queryString(params)}`,
      );
    },
    /** entries: [{value, kind?, comment?, expires_at?}] */
    async addEntries(id, entries) {
      return await fetchWrapper.post(`${baseUrl}/${id}/entries`, { entries });
    },
    async deleteEntries(id, ids) {
      return await fetchWrapper.post(`${baseUrl}/${id}/entries/delete`, {
        ids,
      });
    },
    async importText(id, text, replace = false) {
      return await fetchWrapper.post(`${baseUrl}/${id}/import`, {
        text,
        replace,
      });
    },
    async exportText(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/export`);
    },
    async sync(id) {
      return await fetchWrapper.post(`${baseUrl}/${id}/sync`, {});
    },
    /** {indicator uuid: [ids of your lists it is on]}. */
    async hits(indicators) {
      if (!indicators.length) return {};
      const response = await fetchWrapper.post(`${baseUrl}/hits`, {
        indicators,
      });
      return response.hits;
    },
    /** {value: [{list_name, entry, kind, comment, …}]}: why values match. */
    async explain(values, type = null) {
      const response = await fetchWrapper.post(`${baseUrl}/explain`, {
        values,
        type,
      });
      return response.matches;
    },
  },
});
