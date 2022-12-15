import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/attributes`;

export const useAttributesStore = defineStore({
    id: "attributes",
    state: () => ({
        attributes: {},
        attribute: {},
        page_count: 0,
        status: {
            loading: false,
            error: false
        }
    }),
    actions: {
        async get(params = { skip: 0, limit: 10, event_id: null, deleted: false }) {
            this.status = { loading: true };
            fetchWrapper
            .get(baseUrl + "/?" + new URLSearchParams(params).toString())
            .then((response) => (this.attributes = response, this.page_count = Math.ceil(response.total / params.size)))
            .catch((error) => (this.status = { error }))
            .finally(() => (this.status = { loading: false }));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((attribute) => (this.attribute = attribute))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async create(attribute) {
            this.status = { loading: true };
            return await fetchWrapper
                .post(baseUrl, attribute)
                .then((attribute) => (this.attribute = attribute))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async delete(id) {
            this.status = { loading: true };
            return await fetchWrapper
                .delete(`${baseUrl}/${id}`)
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        }
    },
});
