import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/indicators`;

export const useIndicatorsStore = defineStore({
  id: "indicators",
  state: () => ({
    page: { total: 0, page: 1, size: 50, items: [] },
    indicatorsStatus: null,
    status: { loading: false, error: false },
    // Explore's Indicators tab, in the {total, results: [{_id, _source}]}
    // shape its other tabs use.
    explore_docs: null,
    explore_page_count: 0,
    exploreStatus: { loading: false, error: false, exporting: false },
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
    async exploreSearch({ query, page = 1, size = 5, sort = "score" }) {
      this.exploreStatus.loading = true;
      this.exploreStatus.error = false;
      const params = new URLSearchParams({ q: query, page, size, sort });
      return fetchWrapper
        .get(`${baseUrl}?${params}`)
        .then((response) => {
          this.explore_docs = {
            total: response.total,
            results: response.items.map((i) => ({ _id: i.uuid, _source: i })),
          };
          this.explore_page_count = Math.ceil(response.total / size);
        })
        .catch((error) => (this.exploreStatus.error = error))
        .finally(() => (this.exploreStatus.loading = false));
    },
    /** Every indicator matching a query, as JSON (for Explore's download). */
    async exportAll(query) {
      this.exploreStatus.exporting = true;
      const params = new URLSearchParams({ query, format: "ndjson" });
      try {
        const text = await fetchWrapper.get(`${baseUrl}/export?${params}`);
        return String(text)
          .split("\n")
          .filter(Boolean)
          .map((line) => JSON.parse(line));
      } finally {
        this.exploreStatus.exporting = false;
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
