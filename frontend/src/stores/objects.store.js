import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/objects`;

export const useObjectsStore = defineStore({
    id: "objects",
    state: () => ({
        objects: {},
        object: {},
    }),
    actions: {
        async get(params = { skip: 0, limit: 10, event_id: null }) {
            this.objects = { loading: true };
            fetchWrapper
                .get(baseUrl + "/?" + new URLSearchParams(params).toString())
                .then((objects) => (this.objects = objects))
                .catch((error) => (this.objects = { error }));
        },
        async getById(id) {
            this.object = { loading: true };
            fetchWrapper
                .get(`${baseUrl}/${id}`)
                .then((object) => (this.object = object))
                .catch((error) => (this.object = { error }));
        }
    },
});
