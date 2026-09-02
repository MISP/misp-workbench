import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/analyst-data`;
const apiUrl = import.meta.env.VITE_API_URL;

// Where a relationship target is read from, and how it is labelled, per type.
// Types outside this map (GalaxyCluster and friends, which can arrive over
// sync) are shown as a bare uuid rather than guessed at.
const targetSources = {
  Event: {
    url: (uuid) => `${apiUrl}/events/${uuid}`,
    label: (r) => r.info || "(no info)",
    sublabel: () => null,
    route: (uuid) => `/events/${uuid}`,
  },
  Attribute: {
    url: (uuid) => `${apiUrl}/attributes/${uuid}`,
    label: (r) => r.value ?? "",
    sublabel: (r) => [r.type, r.category].filter(Boolean).join(" · ") || null,
    route: (uuid) => `/attributes/${uuid}`,
  },
  Object: {
    url: (uuid) => `${apiUrl}/objects/${uuid}`,
    label: (r) => r.name ?? "",
    sublabel: (r) => r.comment || r.description || null,
    route: (uuid) => `/objects/${uuid}`,
  },
};

// In-flight lookups, so several relationships pointing at the same record
// resolve on one request. Deliberately outside the store state: it holds
// promises, which do not belong in reactive data.
const inFlight = new Map();

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
    // resolved relationship targets, keyed "Type:uuid"
    targets: {},
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
    // null until resolved; { label, sublabel, route, missing } afterwards
    targetFor: (state) => (objectType, objectUuid) =>
      state.targets[`${objectType}:${objectUuid}`] ?? null,
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
    /**
     * Look up what a relationship points at, so it can be shown by name and
     * linked rather than as a bare uuid.
     *
     * Cached by type and uuid, and de-duplicated while in flight. Reads
     * through fetchWrapper rather than the events/attributes/objects stores
     * because their getById actions overwrite the record the page is showing.
     */
    async resolveTarget(objectType, objectUuid) {
      if (!objectType || !objectUuid) return null;

      const key = `${objectType}:${objectUuid}`;
      if (this.targets[key]) return this.targets[key];
      if (inFlight.has(key)) return inFlight.get(key);

      const source = targetSources[objectType];
      if (!source) {
        // a type this UI has no page for: record it so callers stop asking
        const unknown = {
          label: null,
          sublabel: null,
          route: null,
          missing: false,
        };
        this.targets = { ...this.targets, [key]: unknown };
        return unknown;
      }

      const request = fetchWrapper
        .get(source.url(objectUuid))
        .then((record) => ({
          label: source.label(record) || objectUuid,
          sublabel: source.sublabel(record),
          route: source.route(objectUuid),
          missing: false,
        }))
        // deleted, or never synced: say so instead of linking into a 404
        .catch(() => ({
          label: null,
          sublabel: null,
          route: null,
          missing: true,
        }))
        .then((resolved) => {
          this.targets = { ...this.targets, [key]: resolved };
          inFlight.delete(key);
          return resolved;
        });

      inFlight.set(key, request);
      return request;
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
