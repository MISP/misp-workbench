import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/users`;

export const useUsersStore = defineStore({
  id: "users",
  state: () => ({
    users: {},
  }),
  actions: {
    async getAll() {
      this.users = { loading: true };
      fetchWrapper
        .get(baseUrl)
        .then((users) => (this.users = users))
        .catch((error) => (this.users = { error }));
    },
    async getById(id) {
      this.user = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((user) => (this.user = user))
        .catch((error) => (this.user = { error }));
    }
  },
});
