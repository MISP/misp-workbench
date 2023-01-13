import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/servers`;

export const useServersStore = defineStore({
    id: "servers",
    state: () => ({
        servers: {},
        server: {},
        status: {
            loading: false,
            updating: false,
            creating: false,
            error: false
        }
    }),
    actions: {
        async getAll() {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((servers) => (this.servers = servers))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((server) => (this.server = server))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async create(server) {
            this.status = { creating: true };
            return await fetchWrapper
                .post(baseUrl, server)
                .then((response) => (this.server = response))
                .finally(() => (this.status = { creating: false }));
        },
    },
});
