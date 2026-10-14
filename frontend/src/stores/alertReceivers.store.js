import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const apiUrl = import.meta.env.VITE_API_URL;
const baseUrl = `${apiUrl}/alert-receivers`;

// Inbound alert webhooks: your organisation's (every one, for admins).
export const useAlertReceiversStore = defineStore({
  id: "alertReceivers",
  state: () => ({
    receivers: [],
    presets: [],
    // A receiver just created: its id and URL, shown once on its page.
    fresh: null,
    status: { loading: false, error: false },
  }),
  getters: {
    presetsById: (state) =>
      Object.fromEntries(state.presets.map((p) => [p.preset, p])),
  },
  actions: {
    async getAll() {
      this.status.loading = true;
      this.status.error = false;
      return fetchWrapper
        .get(baseUrl)
        .then((receivers) => (this.receivers = receivers))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    /** The senders with a ready mapping, their setup and a sample body. */
    async getPresets() {
      if (!this.presets.length) {
        this.presets = await fetchWrapper.get(`${baseUrl}/presets`);
      }
      return this.presets;
    },
    async get(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}`);
    },
    /** A new receiver; its token (and URL) is in this response only. */
    async create(receiver) {
      return await fetchWrapper.post(baseUrl, receiver);
    },
    async update(id, receiver) {
      return await fetchWrapper.patch(`${baseUrl}/${id}`, receiver);
    },
    async remove(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    /** A new token; the old one stops working. In this response only. */
    async rotateToken(id) {
      return await fetchWrapper.post(`${baseUrl}/${id}/token`);
    },
    async lastPayload(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/last-payload`);
    },
    /** What a body would report with a mapping; nothing is written. */
    async test(mapping, payload, onlyKnown, name) {
      return await fetchWrapper.post(`${baseUrl}/test`, {
        mapping,
        payload,
        only_known: onlyKnown,
        name,
      });
    },
    /** The full URL senders post to, from a token's path. */
    urlOf(path) {
      return `${apiUrl}${path}`;
    },
  },
});
