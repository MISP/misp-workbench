import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/feeds`;

export const useFeedsStore = defineStore({
    id: "feeds",
    state: () => ({
        feeds: {},
        feed: {},
        testConnection: {},
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
                .then((feeds) => (this.feeds = feeds))
                .catch((error) => (this.status.error = error))
                .finally(() => (this.status.loading = false));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((feed) => (this.feed = feed))
                .catch((error) => (this.status = { error }))
                .finally(() => (this.status.loading = false));
        },
        async create(feed) {
            this.status = { creating: true };
            return await fetchWrapper
                .post(baseUrl, feed)
                .then((response) => (this.feed = response))
                .catch((error) => (this.status.error = error))
                .finally(() => (this.status.creating = false));
        },
        async update(feed) {
            this.status = { updating: true };
            fetchWrapper
                .patch(`${baseUrl}/${feed.id}`, feed)
                .then((response) => (this.feed = response))
                .catch((error) => (this.status.error = error))
                .finally(() => (this.status.updating = false));
        },
        async delete(id) {
            this.status = { loading: true };
            return await fetchWrapper
                .delete(`${baseUrl}/${id}`)
                .catch((error) => (this.status.error = error))
                .finally(() => (this.status.loading = false));
        },
        async toggleEnable(feed) {
            this.status = { updating: true };
            return fetchWrapper
                .patch(`${baseUrl}/${feed.id}`, {
                    enabled: !feed.enabled,
                })
                .finally(() => (this.status.updating = false));
        },
        async fetch(id) {
            return await fetchWrapper
                .post(`${baseUrl}/${id}/fetch`)
                .catch((error) => (this.status.error = error))
        }
    },
});
