import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tech-lab/reactor`;

export const useReactorStore = defineStore({
  id: "reactor",
  state: () => ({
    scripts: null,
    script: null,
    runs: null,
    runsPage: 1,
    runsSize: 100,
    status: {
      loading: false,
      creating: false,
      updating: false,
      testing: false,
      loadingMoreRuns: false,
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
        .get(`${baseUrl}/scripts/?${queryString}`)
        .then((scripts) => (this.scripts = scripts))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getById(id) {
      this.status.loading = true;
      return fetchWrapper
        .get(`${baseUrl}/scripts/${id}`)
        .then((script) => (this.script = script))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async getSource(id) {
      return fetchWrapper.get(`${baseUrl}/scripts/${id}/source`);
    },
    async create(payload) {
      this.status.creating = true;
      return await fetchWrapper
        .post(`${baseUrl}/scripts/`, payload)
        .finally(() => (this.status.creating = false));
    },
    async update(id, payload) {
      this.status.updating = true;
      return await fetchWrapper
        .patch(`${baseUrl}/scripts/${id}`, payload)
        .finally(() => (this.status.updating = false));
    },
    async delete(id) {
      return await fetchWrapper.delete(`${baseUrl}/scripts/${id}`);
    },
    async getRuns(id, params = {}) {
      const size = params.size ?? this.runsSize;
      const page = params.page ?? 1;
      const queryString = new URLSearchParams({
        page,
        size,
        ...params,
      }).toString();
      return fetchWrapper
        .get(`${baseUrl}/scripts/${id}/runs?${queryString}`)
        .then((runs) => {
          this.runs = runs;
          this.runsPage = page;
          this.runsSize = size;
          return runs;
        });
    },
    async loadMoreRuns(id) {
      if (!this.runs) return;
      this.status.loadingMoreRuns = true;
      const nextPage = this.runsPage + 1;
      const queryString = new URLSearchParams({
        page: nextPage,
        size: this.runsSize,
      }).toString();
      return fetchWrapper
        .get(`${baseUrl}/scripts/${id}/runs?${queryString}`)
        .then((page) => {
          this.runs = {
            ...page,
            items: [...(this.runs?.items ?? []), ...(page.items ?? [])],
          };
          this.runsPage = nextPage;
          return page;
        })
        .finally(() => (this.status.loadingMoreRuns = false));
    },
    async getRunLog(runId) {
      return fetchWrapper.get(`${baseUrl}/runs/${runId}/log`);
    },
    async getRunProfile(runId) {
      // Resolves to null when the run wasn't profiled (404) so callers can
      // omit the chart without raising.
      try {
        return await fetchWrapper.get(`${baseUrl}/runs/${runId}/profile`);
      } catch (err) {
        if (err?.status === 404) return null;
        throw err;
      }
    },
    async test(id, payload = {}) {
      this.status.testing = true;
      return await fetchWrapper
        .post(`${baseUrl}/scripts/${id}/test`, { payload })
        .finally(() => (this.status.testing = false));
    },
    async saveAndTest({
      scriptId,
      payload,
      scriptPayload,
      testPayload,
      trigger,
      profile = false,
    }) {
      this.status.testing = true;
      try {
        let id = scriptId;
        if (id) {
          await fetchWrapper.patch(`${baseUrl}/scripts/${id}`, scriptPayload);
        } else {
          const created = await fetchWrapper.post(
            `${baseUrl}/scripts/`,
            scriptPayload,
          );
          id = created.id;
        }
        const body = { payload: testPayload ?? payload ?? {} };
        if (trigger?.resource_type) body.resource_type = trigger.resource_type;
        if (trigger?.action) body.action = trigger.action;
        const url = profile
          ? `${baseUrl}/scripts/${id}/test?profile=true`
          : `${baseUrl}/scripts/${id}/test`;
        const run = await fetchWrapper.post(url, body);
        const log = await fetchWrapper.get(`${baseUrl}/runs/${run.id}/log`);
        let flameTree = null;
        if (profile) {
          const resp = await this.getRunProfile(run.id);
          flameTree = resp?.tree ?? null;
        }
        return { scriptId: id, run, log: log.log, flameTree };
      } finally {
        this.status.testing = false;
      }
    },
  },
});
