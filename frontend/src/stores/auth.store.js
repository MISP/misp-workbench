import { defineStore } from "pinia";

import jwt_decode from "jwt-decode";

import { fetchWrapper } from "@/helpers";
import { router } from "@/router";

export const useAuthStore = defineStore({
  id: "auth",
  state: () => {
    const token = localStorage.getItem("access_token");
    const refresh_token = localStorage.getItem("refresh_token");
    const decoded = token ? jwt_decode(token) : null;

    return {
      access_token: token,
      refresh_token: refresh_token,
      decoded_access_token: decoded,
      scopes: decoded?.scopes || [],
      returnUrl: null,
    };
  },
  actions: {
    async authenticate(username, password) {
      const response = await fetchWrapper.authenticate(username, password);

      this.access_token = response.access_token;
      this.refresh_token = response.refresh_token;
      this.decoded_access_token = jwt_decode(this.access_token);

      this.scopes = this.decoded_access_token.scopes;

      localStorage.setItem("access_token", this.access_token);
      localStorage.setItem("refresh_token", this.refresh_token);

      router.push("/events");
    },
    isAuthenticated() {
      return (
        !!this.access_token &&
        !!this.decoded_access_token &&
        this.decoded_access_token.exp > Date.now() / 1000
      );
    },
    async revokeToken() {
      if (this.access_token) {
        await fetchWrapper.post(`${import.meta.env.VITE_API_URL}/auth/logout`, {
          token: this.access_token,
        });
      }
    },
    async logout() {
      await this.revokeToken();
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      this.$reset();
      router.push("/login");
    },
  },
});
