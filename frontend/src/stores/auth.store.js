import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";
import { router } from "@/router";

export const useAuthStore = defineStore({
  id: "auth",
  state: () => ({
    access_token: localStorage.getItem("access_token"),
    returnUrl: null,
  }),
  actions: {
    async authenticate(username, password) {
      const response = await fetchWrapper.authenticate(username, password);

      this.access_token = response.access_token;

      localStorage.setItem(
        "access_token",
        response.access_token
      );

      router.push("/");
    },
    isAuthenticated() {
      return !!this.access_token;
    },
    logout() {
      localStorage.removeItem("access_token");
      this.$reset();
      router.push("/login");
    },
  }
});
