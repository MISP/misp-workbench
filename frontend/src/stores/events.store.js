import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/events`;

export const useEventsStore = defineStore({
    id: "events",
    state: () => ({
        events: {},
        event: {},
        status: {
            loading: false,
            updating: false,
            error: false
        }
    }),
    actions: {
        async getAll() {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl)
                .then((events) => (this.events = events))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((event) => (this.event = event))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async update(event) {
            this.status = { updating: true };
            fetchWrapper
                .patch(`${baseUrl}/${event.id}`, event)
                .then((event) => (this.event = event))
                .catch((error) => (this.error = error))
                .finally(() => (this.status = { updating: false }));
        }
    },
});
