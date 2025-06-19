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
        `${baseUrl}/events/${id}/upload_attachments`,
        files,
      );
    },
    async getEventAttachments(uuid) {
      return await fetchWrapper
        .get(`${baseUrl}/events/${uuid}/attachments`)
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
    async downloadAttachment(id) {
      return await fetchWrapper.downloadAttachment(
        `${baseUrl}/attachments/${id}`,
      );
    },
  },
});
