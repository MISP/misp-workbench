import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tasks`;

export const useTasksStore = defineStore({
  id: "tasks",
  state: () => ({
    tasks: {},
    workers: {},
    task: {},
    status: {
      loading: false,
      error: false,
    },
  }),
  actions: {
    async get_tasks() {
      this.status = { loading: true };
      fetchWrapper
        .get(baseUrl)
        .then((response) => (this.tasks = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async get_workers() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/workers`)
        .then((response) => (this.workers = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async getTaskById(id) {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/${id}`)
        .then((task) => (this.task = task))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
