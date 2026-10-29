import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/diagnostics`;

export const useDiagnosticsStore = defineStore({
  id: "diagnostics",
  state: () => ({
    opensearch: null,
    redis: null,
    postgres: null,
    storage: null,
    modules: null,
    lab: null,
    queues: null,
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
    async getRedis() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/redis`)
        .then((response) => (this.redis = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getPostgres() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/postgres`)
        .then((response) => (this.postgres = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getStorage() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/storage`)
        .then((response) => (this.storage = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getModules() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/modules`)
        .then((response) => (this.modules = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getQueues() {
      return fetchWrapper
        .get(`${baseUrl}/queues`)
        .then((response) => (this.queues = response))
        .catch((error) => (this.queues = { connected: false, error }));
    },
    async getLab() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/lab`)
        .then((response) => (this.lab = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
