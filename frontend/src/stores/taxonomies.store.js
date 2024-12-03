import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/taxonomies`;

export const useTaxonomiesStore = defineStore({
    id: "taxonomies",
    state: () => ({
        taxonomies: {},
        taxonomy: {},
        page_count: 0,
        status: {
            loading: false,
            error: false
        }
    }),
    actions: {
        async get(params = { page: 1, size: 10, deleted: false }) {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams(params).toString())
                .then((response) => (this.taxonomies = response, this.page_count = Math.ceil(response.total / params.size)))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
    },
});
