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
      isRefreshing: false,
      refreshPromise: null,
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
    async refreshAccessToken() {
      if (this.isRefreshing) {
        return this.refreshPromise;
      }

      this.isRefreshing = true;

      this.refreshPromise = (async () => {
        if (!this.refresh_token) {
          throw new Error("No refresh token");
        }

        const response = await fetch(
          `${import.meta.env.VITE_API_URL}/auth/refresh`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              refresh_token: this.refresh_token,
            }),
          },
        );

        if (!response.ok) {
          router.push("/login");
          throw new Error("Failed to refresh token");
        }

        const data = await response.json();

        this.access_token = data.access_token;
        this.refresh_token = data.refresh_token;
        this.decoded_access_token = jwt_decode(this.access_token);
        this.scopes = this.decoded_access_token.scopes;

        localStorage.setItem("access_token", this.access_token);
        localStorage.setItem("refresh_token", this.refresh_token);
      })();

      try {
        await this.refreshPromise;
      } finally {
        this.isRefreshing = false;
      }

      return this.access_token;
    },
    async ensureValidToken() {
      if (!this.access_token || !this.decoded_access_token) {
        return;
      }

      const now = Date.now() / 1000;
      const buffer = 30; // seconds before expiration to refresh

      if (this.decoded_access_token.exp - now < buffer) {
        await this.refreshAccessToken();
      }
    },
  },
});
