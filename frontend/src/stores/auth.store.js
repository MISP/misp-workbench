import { defineStore } from "pinia";

import jwt_decode from "jwt-decode";

import { fetchWrapper } from "@/helpers";
import { router } from "@/router";

export const useAuthStore = defineStore({
  id: "auth",
  state: () => ({
    access_token: localStorage.getItem("access_token"),
    decoded_access_token: JSON.parse(localStorage.getItem("decoded_access_token")) || {},
    returnUrl: null,
  }),
  actions: {
    async authenticate(username, password) {
      const response = await fetchWrapper.authenticate(username, password);

      this.access_token = response.access_token;
      this.decoded_access_token = jwt_decode(this.access_token);

      localStorage.setItem(
        "access_token",
        this.access_token
      );

      localStorage.setItem(
        "decoded_access_token",
        JSON.stringify(this.decoded_access_token)
      );

      router.push("/");
    },
    isAuthenticated() {
      console.log(!!this.access_token && !!this.decoded_access_token && this.decoded_access_token.exp > Date.now() / 1000);
      console.log(!!this.access_token);
      console.log(!!this.decoded_access_token);
      console.log(this.decoded_access_token.exp > Date.now() / 1000);
      return !!this.access_token && !!this.decoded_access_token && this.decoded_access_token.exp > Date.now() / 1000;
    },
    logout() {
      localStorage.removeItem("access_token");
      this.$reset();
      router.push("/login");
    },
  }
});
