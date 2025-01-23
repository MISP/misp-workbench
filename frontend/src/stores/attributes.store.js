import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/attributes`;

export const useAttributesStore = defineStore({
  id: "attributes",
  state: () => ({
    attributes: {},
    attribute: {},
    page_count: 0,
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { skip: 0, limit: 10, event_id: null, deleted: false }) {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl + "/?" + new URLSearchParams(params).toString())
        .then(
          (response) => (
            (this.attributes = response),
            (this.page_count = Math.ceil(response.total / params.size))
          )
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((attribute) => (this.attribute = attribute))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async create(attribute) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(baseUrl, attribute)
        .then((attribute) => (this.attribute = attribute))
        .finally(() => (this.status = { loading: false }));
    },
    async update(attribute) {
      this.status = { updating: true };
      fetchWrapper
        .patch(`${baseUrl}/${attribute.id}`, attribute)
        .then((response) => (this.attribute = response))
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
  },
});
