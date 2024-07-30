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
    },
});
