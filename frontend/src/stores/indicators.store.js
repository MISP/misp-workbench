import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/indicators`;

export const useIndicatorsStore = defineStore({
  id: "indicators",
  state: () => ({
    page: { total: 0, page: 1, size: 50, items: [] },
    indicatorsStatus: null,
    status: { loading: false, error: false },
  }),
  actions: {
    /** One page of consolidated indicators (one per type + value). */
    async search(params = {}) {
      this.status.loading = true;
      this.status.error = false;
      const query = new URLSearchParams(
        Object.entries(params).filter(
          ([, v]) => v !== null && v !== undefined && v !== "",
        ),
      );
      return fetchWrapper
        .get(`${baseUrl}?${query}`)
        .then((page) => (this.page = page))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    /**
     * Scores of the indicators behind attributes (type + value), keyed by
     * attribute uuid; attributes without an indicator are left out.
     */
    async scoresFor(attributes) {
      const items = (attributes || []).filter((a) => a.type && a.value);
      if (!items.length) return {};
      const response = await fetchWrapper.post(`${baseUrl}/scores`, {
        attributes: items.map((a) => ({ type: a.type, value: a.value })),
      });
      const scores = {};
      items.forEach((a, i) => {
        if (response.scores[i]) scores[a.uuid] = response.scores[i];
      });
      return scores;
    },
    /** Volume, overlap, hit and false-positive rates of every source. */
    async sourceQuality() {
      return await fetchWrapper.get(`${baseUrl}/sources`);
    },
    /**
     * One source's quality: kind is feed, server, organisation or local;
     * null when it has no indicators yet.
     */
    async sourceQualityFor(kind, key) {
      try {
        return await fetchWrapper.get(
          `${baseUrl}/sources/${kind}/${encodeURIComponent(key ?? "-")}`,
        );
      } catch {
        return null;
      }
    },
    async getStatus() {
      return fetchWrapper
        .get(`${baseUrl}/status`)
        .then((status) => (this.indicatorsStatus = status))
        .catch(() => (this.indicatorsStatus = null));
    },
  },
});
