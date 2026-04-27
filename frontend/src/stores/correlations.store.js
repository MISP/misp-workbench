import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/correlations`;

export const useCorrelationsStore = defineStore("correlations", {
  state: () => ({
    correlations: [],
    correlation_docs: null,
    correlated_events: [],
    stats: {},
    page_count: 0,
    status: {
      loading: false,
      generating: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { page: 1, size: 10 }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/?" + new URLSearchParams(params).toString())
        .then(
          (response) => (
            (this.correlations = response),
            (this.page_count = Math.ceil(response.total / params.size))
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getTopCorrelatingEvents(event_uuid) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/events/" + event_uuid + "/top")
        .then((response) => (this.correlated_events = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async run() {
      this.status = { generating: true };
      return await fetchWrapper
        .post(`${baseUrl}/run`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { generating: false }));
    },
    async search(
      params = {
        page: 1,
        size: 10,
        query: "",
        sort_by: "@timestamp",
        sort_order: "desc",
      },
    ) {
      this.status = { loading: true };
      const queryParams = { ...params, query: params.query || "*" };
      return await fetchWrapper
        .get(baseUrl + "/search?" + new URLSearchParams(queryParams).toString())
        .then((response) => {
          this.correlation_docs = response;
          this.page_count = Math.ceil(response.total / params.size);
          return response;
        })
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async histogram(params = { query: "", interval: "1d" }) {
      const queryParams = { ...params, query: params.query || "*" };
      return await fetchWrapper
        .get(
          baseUrl + "/histogram?" + new URLSearchParams(queryParams).toString(),
        )
        .catch((error) => (this.status = { error }));
    },
    async getStats() {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/stats")
        .then((response) => (this.stats = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
