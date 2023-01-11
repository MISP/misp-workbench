import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/organisations`;

export const useOrganisationsStore = defineStore({
    id: "organisations",
    state: () => ({
        organisations: {},
        organisation: {},
        status: {
            loading: false,
            error: false
        }
    }),
    actions: {
        async getAll() {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((organisations) => (this.organisations = organisations))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((organisation) => (this.organisation = organisation))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async create(organisation) {
            this.status = { creating: true };
            return await fetchWrapper
                .post(baseUrl, organisation)
                .then((response) => (this.organisation = response))
                .finally(() => (this.status = { creating: false }));
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
