import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}`;

export const useAttachmentsStore = defineStore({
  id: "attachments",
  state: () => ({
    attachments: {},
    attachment: {},
    pages: 0,
    page: 0,
    size: 0,
    total: 0,
    status: {
      loading: false,
      updating: false,
      creating: false,
      uploading: false,
      error: false,
    },
  }),
  actions: {
    async uploadAttachments(uuid, files) {
      this.status = { uploading: true };
      return await fetchWrapper.postFormData(
        `${baseUrl}/events/${uuid}/upload_attachments`,
        files,
      );
    },
    async getEventAttachments(uuid, { page = 1, size = 10 } = {}) {
      this.status = { loading: true };
      const qs = new URLSearchParams({ page, size }).toString();
      return await fetchWrapper
        .get(`${baseUrl}/events/${uuid}/attachments?${qs}`)
        .then(
          (response) => (
            (this.attachments = response.items),
            (this.pages = response.pages),
            (this.total = response.total),
            (this.page = response.page),
            (this.size = response.size)
          ),
        )
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async downloadAttachment(uuid) {
      return await fetchWrapper.downloadAttachment(
        `${baseUrl}/attachments/${uuid}`,
      );
    },
  },
});
