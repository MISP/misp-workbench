import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/taxonomies`;

export const useTaxonomiesStore = defineStore({
  id: "taxonomies",
  state: () => ({
    taxonomies: {},
    taxonomy: {},
    page_count: 0,
    status: {
      loading: false,
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
            (this.taxonomies = response),
            (this.page_count = Math.ceil(response.total / params.size))
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((taxonomy) => (this.taxonomy = taxonomy))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async delete(id) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async toggle(property, taxonomy) {
      this.status = { updating: true };
      const patch = {};
      patch[property] = !taxonomy[property];
      return fetchWrapper
        .patch(`${baseUrl}/${taxonomy.id}`, patch)
        .finally(() => (this.status.updating = false));
    },
    async update(id) {
      this.status = { updating: true };
      return await fetchWrapper
        .post(`${baseUrl}/update/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.updating = false));
    },
  },
});
