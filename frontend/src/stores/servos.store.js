import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tech-lab/servos`;

export const useServosStore = defineStore({
  id: "servos",
  state: () => ({
    servos: null,
    servo: null,
    pipelines: null,
    pipeline: null,
    errors: {},
    runs: [],
    backfillPreview: null,
    templates: null,
    simulation: null,
    status: {
      loading: false,
      loadingPipelines: false,
      creating: false,
      updating: false,
      simulating: false,
      backfilling: false,
      error: false,
    },
  }),
  actions: {
    async getAll(params = {}) {
      this.status.loading = true;
      const queryString = new URLSearchParams({
        page: 1,
        size: 50,
        ...params,
      }).toString();
      return fetchWrapper
        .get(`${baseUrl}/?${queryString}`)
        .then((servos) => (this.servos = servos))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((servo) => (this.servo = servo))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getPipelines() {
      this.status.loadingPipelines = true;
      return fetchWrapper
        .get(`${baseUrl}/pipelines`)
        .then((pipelines) => (this.pipelines = pipelines))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loadingPipelines = false));
    },
    async getPipeline(name) {
      return fetchWrapper
        .get(`${baseUrl}/pipelines/${encodeURIComponent(name)}`)
        .then((pipeline) => (this.pipeline = pipeline));
    },
    async getTemplates() {
      if (this.templates) return this.templates;
      return fetchWrapper
        .get(`${baseUrl}/templates`)
        .then((templates) => (this.templates = templates));
    },
    async create(payload) {
      this.status.creating = true;
      return await fetchWrapper
        .post(`${baseUrl}/`, payload)
        .finally(() => (this.status.creating = false));
    },
    async update(id, payload) {
      this.status.updating = true;
      return await fetchWrapper
        .patch(`${baseUrl}/${id}`, payload)
        .finally(() => (this.status.updating = false));
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    async getErrors() {
      // A servo that throws does not stop ingestion, so this aggregation is
      // the only place those failures are visible.
      return fetchWrapper
        .get(`${baseUrl}/errors`)
        .then((errors) => (this.errors = errors))
        .catch(() => (this.errors = {}));
    },
    async reorder(servoIds) {
      return await fetchWrapper.post(`${baseUrl}/reorder`, {
        servo_ids: servoIds,
      });
    },
    async previewBackfill(filterQuery) {
      const qs = new URLSearchParams(
        filterQuery ? { filter_query: filterQuery } : {},
      ).toString();
      return fetchWrapper
        .get(`${baseUrl}/backfill/preview${qs ? `?${qs}` : ""}`)
        .then((preview) => (this.backfillPreview = preview));
    },
    async startBackfill(filterQuery) {
      this.status.backfilling = true;
      return await fetchWrapper
        .post(`${baseUrl}/backfill`, { filter_query: filterQuery || null })
        .finally(() => (this.status.backfilling = false));
    },
    async getRuns() {
      return fetchWrapper
        .get(`${baseUrl}/runs`)
        .then((runs) => (this.runs = runs))
        .catch(() => (this.runs = []));
    },
    async simulate(payload) {
      this.status.simulating = true;
      return await fetchWrapper
        .post(`${baseUrl}/simulate`, payload)
        .then((result) => (this.simulation = result))
        .finally(() => (this.status.simulating = false));
    },
  },
});
