import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useServersStore = defineStore({
    id: "servers",
    state: () => ({
        servers: {},
        server: {},
    }),
    actions: {
        async getAll() {
            this.servers = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((servers) => (this.servers = servers))
                .catch((error) => (this.servers = { error }));
        },
        async getById(id) {
            this.server = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((server) => (this.server = server))
                .catch((error) => (this.server = { error }));
        }
    },
});
