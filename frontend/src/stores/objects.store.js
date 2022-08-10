import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/objects`;

export const useObjectsStore = defineStore({
    id: "objects",
    state: () => ({
        objects: {},
        object: {},
        status: {
            loading: false,
            error: false
        }
    }),
    actions: {
        async get(params = { skip: 0, limit: 10, event_id: null }) {
            this.status = { loading: true };
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams(params).toString())
                .then((objects) => (this.objects = objects))
                .catch((error) => (this.objects = { error }))
                .finally(() => (this.status = { loading: false }));
        },
        async getById(id) {
            this.status = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((object) => (this.object = object))
                .catch((error) => (this.object = { error }))
                .finally(() => (this.status = { loading: false }));
        }
    },
});
