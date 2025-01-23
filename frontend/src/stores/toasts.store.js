import { defineStore } from "pinia";

export const useToastsStore = defineStore({
  id: "toasts",
  state: () => ({
    toasts: [],
    nextId: 0,
  }),
  actions: {
    push(msg, type = "info") {
      if (type === "error") {
        type = "text-bg-error";
      }
      if (type === "success") {
        type = "text-bg-success";
      }
      if (type === "info") {
        type = "text-bg-white";
      }
      if (type === "warning") {
        type = "text-bg-warning";
      }

      this.toasts.push({
        id: (this.nextId += 1),
        message: msg,
        type: type,
      });

      setTimeout(() => {
        this.toasts.shift();
      }, 3000);
    },
    remove(id) {
      this.toasts = this.toasts.filter((toast) => toast.id !== id);
    },
  },
});
