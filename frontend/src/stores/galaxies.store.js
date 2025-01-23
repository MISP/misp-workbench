import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/galaxies`;

export const useGalaxiesStore = defineStore({
  id: "galaxies",
  state: () => ({
    galaxies: {},
    galaxy: {},
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
            (this.galaxies = response),
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
        .then((galaxy) => (this.galaxy = galaxy))
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
    async toggle(property, galaxy) {
      this.status = { updating: true };
      const patch = {};
      patch[property] = !galaxy[property];
      return fetchWrapper
        .patch(`${baseUrl}/${galaxy.id}`, patch)
        .finally(() => (this.status.updating = false));
    },
    async update(id) {
      this.status = { updating: true };
      return await fetchWrapper
        .post(`${baseUrl}/update`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status.updating = false));
    },
  },
});
