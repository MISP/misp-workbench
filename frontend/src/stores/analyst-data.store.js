import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/analyst-data`;

// Endpoint path per analyst data type. The type is also what the API expects
// as `object_type` when attaching analyst data to other analyst data.
const collections = {
  Note: "notes",
  Opinion: "opinions",
  Relationship: "relationships",
};

export const useAnalystDataStore = defineStore({
  id: "analystData",
  state: () => ({
    // threads keyed by the object uuid they were fetched for, so several
    // AnalystDataIndex instances (event, attributes, objects) can coexist
    // on one page without overwriting each other
    threads: {},
    // analyst data totals keyed by object uuid, fetched per event so a page of
    // attribute rows can be badged from one request
    counts: {},
    relationshipTypes: [],
    status: {
      loading: false,
      creating: false,
      updating: false,
      deleting: false,
      error: null,
    },
  }),
  getters: {
    hasThreadsFor: (state) => (objectUuid) =>
      Object.prototype.hasOwnProperty.call(state.threads, objectUuid),
    countFromEvent: (state) => (objectUuid) => state.counts[objectUuid] ?? 0,
    threadsFor: (state) => (objectUuid) =>
      state.threads[objectUuid] ?? {
        notes: [],
        opinions: [],
        relationships: [],
      },
    countFor: (state) => (objectUuid) => {
      const thread = state.threads[objectUuid];
      if (!thread) return 0;

      // every node in the tree, replies included
      const count = (nodes) =>
        (nodes ?? []).reduce(
          (total, node) =>
            total +
            1 +
            count(node.notes) +
            count(node.opinions) +
            count(node.relationships),
          0,
        );

      return (
        count(thread.notes) +
        count(thread.opinions) +
        count(thread.relationships)
      );
    },
  },
  actions: {
    async getByEventUuid(event_uuid) {
      this.status = { loading: true, error: null };
      return await fetchWrapper
        .get(`${baseUrl}/events/${event_uuid}`)
        .then((threads) => {
          this.threads = { ...this.threads, [event_uuid]: threads };
          return threads;
        })
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getByObjectUuid(object_uuid, object_type) {
      this.status = { loading: true, error: null };
      const query = object_type
        ? `?${new URLSearchParams({ object_type }).toString()}`
        : "";

      return await fetchWrapper
        .get(`${baseUrl}/objects/${object_uuid}${query}`)
        .then((threads) => {
          this.threads = { ...this.threads, [object_uuid]: threads };
          return threads;
        })
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getCountsByEventUuid(event_uuid) {
      return await fetchWrapper
        .get(`${baseUrl}/events/${event_uuid}/counts`)
        .then((counts) => (this.counts = counts ?? {}))
        .catch((error) => (this.status.error = error));
    },
    async getRelationshipTypes() {
      // the vocabulary does not change between requests, so fetch it once
      if (this.relationshipTypes.length > 0) return this.relationshipTypes;

      return await fetchWrapper
        .get(`${baseUrl}/relationship-types`)
        .then((types) => (this.relationshipTypes = types))
        .catch((error) => (this.status.error = error));
    },
    async create(analyst_type, payload) {
      this.status = { creating: true, error: null };
      return await fetchWrapper
        .post(`${baseUrl}/${collections[analyst_type]}`, payload)
        .catch((error) => {
          this.status.error = error;
          throw error;
        })
        .finally(() => (this.status.creating = false));
    },
    async update(analyst_uuid, payload) {
      this.status = { updating: true, error: null };
      return await fetchWrapper
        .put(`${baseUrl}/${analyst_uuid}`, payload)
        .catch((error) => {
          this.status.error = error;
          throw error;
        })
        .finally(() => (this.status.updating = false));
    },
    async delete(analyst_uuid) {
      this.status = { deleting: true, error: null };
      return await fetchWrapper
        .delete(`${baseUrl}/${analyst_uuid}`)
        .catch((error) => {
          this.status.error = error;
          throw error;
        })
        .finally(() => (this.status.deleting = false));
    },
  },
});
