import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/events`;

export const useEventsStore = defineStore({
    id: "events",
    state: () => ({
        events: {},
        event: {},
    }),
    actions: {
        async getAll() {
            this.events = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((events) => (this.events = events))
                .catch((error) => (this.events = { error }));
        },
        async getById(id) {
            this.event = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((event) => (this.event = event))
                .catch((error) => (this.event = { error }));
        }
    },
});
