import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/roles`;

export const useRolesStore = defineStore({
  id: "objects",
  state: () => ({
    roles: {},
    role: {},
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
        .catch((error) => (this.role = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
