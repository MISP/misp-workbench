import { defineStore } from "pinia";

import { fetchWrapper } from "@/helpers";

const apiUrl = import.meta.env.VITE_API_URL;
const resources = { feed: "feeds", server: "servers" };

// After a fetch or pull is triggered, its run only shows up once a worker
// picks the task up: keep checking for this long.
const EXPECT_MS = 60_000;

function runUrl(kind, id) {
  return `${apiUrl}/${resources[kind]}/${id}/run`;
}

// Feed fetches and server pulls: the run in progress and the last finished
// one, per source ("feed:5", "server:2").
export const useIngestRunsStore = defineStore({
  id: "ingestRuns",
  state: () => ({
    runs: {},
    expecting: {},
  }),
  actions: {
    async load(kind, id) {
      const key = `${kind}:${id}`;
      const run = await fetchWrapper.get(runUrl(kind, id));
      this.runs[key] = run;
      if (run.current) {
        delete this.expecting[key];
      }
      return run;
    },
    async cancel(kind, id) {
      const run = await fetchWrapper.delete(runUrl(kind, id));
      this.runs[`${kind}:${id}`] = run;
      return run;
    },
    expect(kind, id) {
      this.expecting[`${kind}:${id}`] = Date.now() + EXPECT_MS;
    },
    isExpecting(kind, id) {
      return (this.expecting[`${kind}:${id}`] || 0) > Date.now();
    },
  },
});
