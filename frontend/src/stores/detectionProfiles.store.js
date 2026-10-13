import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/detection-profiles`;

export const useDetectionProfilesStore = defineStore({
  id: "detectionProfiles",
  state: () => ({
    profiles: [],
    status: { loading: false, error: false },
  }),
  actions: {
    async getAll() {
      this.status.loading = true;
      return fetchWrapper
        .get(baseUrl)
        .then((profiles) => (this.profiles = profiles))
        .catch((error) => (this.status.error = error))
        .finally(() => (this.status.loading = false));
    },
    async get(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}`);
    },
    async create(profile) {
      return await fetchWrapper.post(baseUrl, profile);
    },
    async update(id, profile) {
      return await fetchWrapper.patch(`${baseUrl}/${id}`, profile);
    },
    async remove(id) {
      return await fetchWrapper.delete(`${baseUrl}/${id}`);
    },
    /** {count, sample} of the indicators these (unsaved) rules select. */
    async preview(rules) {
      return await fetchWrapper.post(`${baseUrl}/preview`, { rules });
    },
    /** {query, snapshot}: the profile as a Lucene query on indicators. */
    async query(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/query`);
    },
    async queryFor(rules) {
      return await fetchWrapper.post(`${baseUrl}/query`, { rules });
    },
    async count(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/count`);
    },
    /**
     * What the profile's next run changes against its last release, whether
     * its gate would hold it, its recent runs and outputs. With `rules`, a
     * dry run of those rules instead.
     */
    async changes(id, rules = null) {
      return rules
        ? await fetchWrapper.post(`${baseUrl}/${id}/changes`, { rules })
        : await fetchWrapper.get(`${baseUrl}/${id}/changes`);
    },
    /** Release the changes as they are now; the outputs that waited run. */
    async approveChanges(id) {
      return await fetchWrapper.post(`${baseUrl}/${id}/changes/approve`, {});
    },
  },
});
