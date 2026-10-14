import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const apiUrl = import.meta.env.VITE_API_URL;
const baseUrl = `${apiUrl}/edls`;

// External dynamic lists: your organisation's (every one, for admins).
export const useEdlsStore = defineStore({
  id: "edls",
  state: () => ({
    edls: [],
    vendors: [],
    status: { loading: false, error: false },
  }),
  getters: {
    vendorsById: (state) =>
      Object.fromEntries(state.vendors.map((v) => [v.vendor, v])),
  },
  actions: {
    async getAll() {
      this.status.loading = true;
      this.status.error = false;
      return fetchWrapper
        .get(baseUrl)
        .then((edls) => (this.edls = edls))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    /** The vendors, the lists each takes and its size limit by default. */
    async getVendors() {
      if (!this.vendors.length) {
        this.vendors = await fetchWrapper.get(`${baseUrl}/vendors`);
      }
      return this.vendors;
    },
    async get(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}`);
    },
    async create(edl) {
      return await fetchWrapper.post(baseUrl, edl);
    },
    async update(id, edl) {
      return await fetchWrapper.patch(`${baseUrl}/${id}`, edl);
    },
    async remove(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    async build(id) {
      return await fetchWrapper.post(`${baseUrl}/${id}/build`);
    },
    async preview(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/preview`);
    },
    async tokens(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/tokens`);
    },
    /** A new token; its value (and URL) is in this response only. */
    async createToken(id, token) {
      return await fetchWrapper.post(`${baseUrl}/${id}/tokens`, token);
    },
    async revokeToken(id, tokenId) {
      return await fetchWrapper.delete(`${baseUrl}/${id}/tokens/${tokenId}`);
    },
    /** The full URL a firewall fetches, from a token's path. */
    urlOf(path) {
      return `${apiUrl}${path}`;
    },
  },
});
