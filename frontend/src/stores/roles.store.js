import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/roles`;

export const useRolesStore = defineStore({
  id: "roles",
  state: () => ({
    roles: {},
    role: {},
    availableScopes: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async getAll() {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl)
        .then((roles) => (this.roles = roles))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((role) => (this.role = role))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getAvailableScopes() {
      return fetchWrapper
        .get(`${baseUrl}/scopes`)
        .then((scopes) => (this.availableScopes = scopes))
        .catch((error) => (this.status = { error }));
    },
    async update(id, data) {
      this.status = { updating: true };
      return fetchWrapper
        .patch(`${baseUrl}/${id}`, data)
        .then((role) => (this.role = role))
        .catch((error) => Promise.reject(error))
        .finally(() => (this.status = { updating: false }));
    },
    async delete(id) {
      this.status = { loading: true };
      return fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => Promise.reject(error))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
