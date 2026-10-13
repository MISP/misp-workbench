import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/indicators`;

function queryString(params) {
  return new URLSearchParams(
    Object.entries(params).filter(
      ([, v]) => v !== null && v !== undefined && v !== "",
    ),
  ).toString();
}

export const useIndicatorReviewsStore = defineStore({
  id: "indicatorReviews",
  state: () => ({
    summary: null,
    page: { total: 0, page: 1, size: 50, items: [] },
    status: { loading: false, error: false, deciding: false },
  }),
  actions: {
    async getSummary() {
      return fetchWrapper
        .get(`${baseUrl}/review/summary`)
        .then((summary) => (this.summary = summary))
        .catch(() => (this.summary = null));
    },
    /**
     * One page of the queue (pending) or of a decision list (approved,
     * rejected, snoozed), in the same {total, page, size, items} shape.
     */
    async load(tab, params = {}) {
      this.status.loading = true;
      this.status.error = false;
      const url =
        tab === "pending"
          ? `${baseUrl}/review?${queryString(params)}`
          : `${baseUrl}/review/decisions?${queryString({ ...params, status: tab })}`;
      return fetchWrapper
        .get(url)
        .then((page) => (this.page = page))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    /** Approve, reject, snooze or reopen indicators, by uuid. */
    async decide(indicators, action, extra = {}) {
      this.status.deciding = true;
      try {
        return await fetchWrapper.post(`${baseUrl}/review/decisions`, {
          indicators,
          action,
          ...extra,
        });
      } finally {
        this.status.deciding = false;
      }
    },
    /** The decision on an indicator, and the decisions before it. */
    async detail(uuid) {
      return fetchWrapper.get(`${baseUrl}/${uuid}/review`);
    },
  },
});
