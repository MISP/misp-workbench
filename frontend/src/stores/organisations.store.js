import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/organisations`;

export const useOrganisationsStore = defineStore({
    id: "organisations",
    state: () => ({
        organisations: {},
        organisation: {},
    }),
    actions: {
        async getAll() {
            this.organisations = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((organisations) => (this.organisations = organisations))
                .catch((error) => (this.organisations = { error }));
        },
        async getById(id) {
            this.organisation = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((organisation) => (this.organisation = organisation))
                .catch((error) => (this.organisation = { error }));
        }
    },
});
