import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/modules`;

export const useModulesStore = defineStore({
    id: "modules",
    state: () => ({
        modules: {},
        module: {},
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
        async dismissErrors() {
            this.status = { error: false };
        }
    },
});
