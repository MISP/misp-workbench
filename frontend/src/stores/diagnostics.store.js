import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/diagnostics`;

export const useDiagnosticsStore = defineStore({
  id: "diagnostics",
  state: () => ({
    opensearch: null,
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getOpensearch() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/opensearch`)
        .then((response) => (this.opensearch = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
