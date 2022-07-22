import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/attributes`;

export const useAttributesStore = defineStore({
    id: "attributes",
    state: () => ({
        attributes: {},
        attribute: {},
    }),
    actions: {
        async get(params = { skip: 0, limit: 10, event_id: null }) {
            this.attributes = { loading: true };
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams(params).toString())
                .then((attributes) => (this.attributes = attributes))
                .catch((error) => (this.attributes = { error }));
        },
        async getById(id) {
            this.attribute = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((attribute) => (this.attribute = attribute))
                .catch((error) => (this.attribute = { error }));
        }
    },
});
