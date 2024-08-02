import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/modules`;

export const useModulesStore = defineStore({
    id: "modules",
    state: () => ({
        modules: {},
        module: {},
        moduleResponse: {},
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
                .then((modules) => (this.modules = modules))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async get(params = { enabled: true }) {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams(params).toString())
                .then((modules) => (this.modules = modules))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async toggle(name) {
            let module = this.modules.find((module) => module.name === name);
            module.updating = true;

            fetchWrapper
                .patch(`${baseUrl}/${name}`, { enabled: !module.enabled })
                .then(() =>
                    module.enabled = !module.enabled
                )
                .catch((error) => (this.status = { error }))
                .finally(() => module.updating = false);
        },
        async configure(name, config) {
            let module = this.modules.find((module) => module.name === name);
            module.updating = true;

            fetchWrapper
                .patch(`${baseUrl}/${name}`, { config: config })
                .then(() =>
                    module.config = module.config
                )
                .catch((error) => (this.status = { error }))
                .finally(() => module.updating = false);
        },
        async query(request) {
            this.status = { loading: true };
            this.moduleResponse = {};
            fetchWrapper
                .post(`${baseUrl}/query`, request)
                .then((response) => this.moduleResponse = response)
                .catch((error) => { this.status = { error }; this.moduleResponse = { error: error } })
                .finally(() => (this.status = { loading: false }));
        },
        async dismissErrors() {
            this.status = { error: false };
        }
    },
});
