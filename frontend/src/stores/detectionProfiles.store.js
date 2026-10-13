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
    async count(id) {
      return await fetchWrapper.get(`${baseUrl}/${id}/count`);
    },
  },
});
