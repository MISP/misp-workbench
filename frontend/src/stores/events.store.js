import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/events`;

export const useEventsStore = defineStore({
  id: "events",
  state: () => ({
    events: {},
    event: {},
    page_count: 0,
    status: {
      loading: false,
      updating: false,
      creating: false,
      uploading: false,
      deleting: false,
      indexing: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { page: 1, size: 10, deleted: false }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/?" + new URLSearchParams(params).toString())
        .then(
          (response) => (
            (this.events = response),
            (this.page_count = Math.ceil(response.total / params.size))
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getAll() {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl)
        .then((events) => (this.events = events))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((event) => (this.event = event))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async update(event) {
      this.status = { updating: true };
      fetchWrapper
        .patch(`${baseUrl}/${event.id}`, event)
        .then((response) => (this.event = response))
        .catch((error) => (this.error = error))
        .finally(() => (this.status = { updating: false }));
    },
    async create(user) {
      this.status = { creating: true };
      return await fetchWrapper
        .post(baseUrl, user)
        .then((response) => (this.event = response))
        .finally(() => (this.status = { creating: false }));
    },
    async delete(id) {
      this.status = { deleting: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { deleting: false }));
    },
    async tag(id, tag) {
      return await fetchWrapper
        .post(`${baseUrl}/${id}/tag/${tag}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async untag(id, tag) {
      return await fetchWrapper
        .delete(`${baseUrl}/${id}/tag/${tag}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async forceIndex(uuid) {
      this.status = { indexing: true };
      return await fetchWrapper
        .post(`${baseUrl}/force-index?uuid=${uuid}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { indexing: false }));
    },
    async search(params = { query: "", page: 1, size: 10 }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/search?" + new URLSearchParams(params).toString())
        .then(
          (response) => (
            (this.events = response),
            (this.page_count = Math.ceil(response.total / params.size))
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
