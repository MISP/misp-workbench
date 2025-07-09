import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/sightings`;

export const useSightingsStore = defineStore("sightings", {
  state: () => ({
    sightings: [],
    stats: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getHistogram(params = { period: "7d", interval: "1h" }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/histogram?" + new URLSearchParams(params).toString())
        .then((response) => (this.sightings = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getStats(params = { period: "7d", interval: "1h" }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/stats?" + new URLSearchParams(params).toString())
        .then((response) => (this.stats = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
