import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useServersStore = defineStore({
  id: "servers",
  state: () => ({
    servers: {},
    server: {},
    testConnection: {},
    remote_events: {},
    status: {
      loading: false,
      updating: false,
      creating: false,
      error: false,
    },
  }),
  actions: {
    async getAll() {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl)
        .then((servers) => (this.servers = servers))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((server) => (this.server = server))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async create(server) {
      this.status = { creating: true };
      return await fetchWrapper
        .post(baseUrl, server)
        .then((response) => (this.server = response))
        .finally(() => (this.status = { creating: false }));
    },
    async update(server) {
      this.status = { updating: true };
      fetchWrapper
        .patch(`${baseUrl}/${server.id}`, server)
        .then((response) => (this.server = response))
        .catch((error) => (this.error = error))
        .finally(() => (this.status = { updating: false }));
    },
    async delete(id) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async testConnection(id) {
      return await fetchWrapper
        .post(`${baseUrl}/${id}/test-connection`)
        .catch((error) => (this.status = { error }));
    },
    async pull(id) {
      return await fetchWrapper
        .post(`${baseUrl}/${id}/pull`)
        .catch((error) => (this.status = { error }));
    },
    async get_remote_server_events_index(id) {
      return await fetchWrapper
        .get(`${baseUrl}/${id}/events-index`)
        .then((events) => (this.remote_events = events))
        .catch((error) => (this.status = { error }));
    },
    async pull_remote_misp_event(id, uuid) {
      return await fetchWrapper
        .post(`${baseUrl}/${id}/events/${uuid}/pull`)
        .catch((error) => (this.status = { error }));
    },
  },
});
