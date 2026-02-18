import { defineStore } from "pinia";
import { fetchWrapper } from "@/helpers";

const baseUrl = `${import.meta.env.VITE_API_URL}/tasks`;

export const useTasksStore = defineStore({
  id: "tasks",
  state: () => ({
    tasks: {},
    scheduledTasks: [],
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
    async restart_worker(workerId) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/workers/${workerId}/restart`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async grow_worker(workerId, amount) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/workers/${workerId}/grow?n=${amount}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async shrink_worker(workerId, amount) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/workers/${workerId}/shrink?n=${amount}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async autoscale_worker(workerId, min, max) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/workers/${workerId}/shrink?min=${min}&max=${max}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async get_scheduled_tasks() {
      this.status = { loading: true };
      fetchWrapper
        .get(`${baseUrl}/scheduled`)
        .then((response) => (this.scheduledTasks = response))
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async force_run_scheduled_task(taskId) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/scheduled/${taskId}/run`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async delete_scheduled_task(taskId) {
      this.status = { loading: true };
      return await fetchWrapper
        .delete(`${baseUrl}/scheduled/${taskId}`)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
    async update_scheduled_task(taskId, taskData) {
      const task = this.scheduledTasks.find((t) => t.id === taskId);
      const snapshot = task ? { ...task } : null;
      if (task) Object.assign(task, taskData);
      return await fetchWrapper
        .patch(`${baseUrl}/scheduled/${taskId}`, taskData)
        .then((response) => {
          if (task && response) Object.assign(task, response);
          return response;
        })
        .catch((error) => {
          if (task && snapshot) Object.assign(task, snapshot);
          this.status = { error };
        });
    },
    async create_scheduled_task(taskData) {
      this.status = { loading: true };
      return await fetchWrapper
        .post(`${baseUrl}/schedule`, taskData)
        .catch((error) => (this.status = { error }))
        .finally(() => (this.status = { loading: false }));
    },
  },
});
