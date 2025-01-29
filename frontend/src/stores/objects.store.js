import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/objects`;

export const useObjectsStore = defineStore({
  id: "objects",
  state: () => ({
    objects: {},
    object: {},
    objectTemplates: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get(params = { skip: 0, limit: 10, event_id: null, deleted: false }) {
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
    },
    async getObjectTemplates() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${import.meta.env.VITE_API_URL}/object-templates`)
        .then((objectTemplates) => (this.objectTemplates = objectTemplates))
        .catch((error) => (this.objectTemplates = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    getObjectTemplateByUuid(uuid) {
      return this.objectTemplates.find(
        (objectTemplate) => objectTemplate.uuid === uuid,
      );
    },
    async create(object) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(baseUrl, object)
        .then((object) => (this.object = object))
        .finally(() => (this.status = { loading: false }));
    },
    async update(object) {
      this.status = { loading: true };
      return await fetchWrapper
        .patch(`${baseUrl}/${object.id}`, object)
        .then((object) => (this.object = object))
        .finally(() => (this.status = { loading: false }));
    },
    async delete(id) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/${id}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
