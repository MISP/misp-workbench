<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import Spinner from "@/components/misc/Spinner.vue";
import ApiError from "@/components/misc/ApiError.vue";
import {
  faFileDownload,
  faMagnifyingGlass,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import Paginate from "vuejs-paginate-next";

import { useLocalStorageRef, fetchWrapper } from "@/helpers";

import AttributeResultCard from "./AttributeResultCard.vue";
import EventResultCard from "./EventResultCard.vue";

const searchQuery = ref("");
const searchAttributes = useLocalStorageRef("exploreSearchAttributes", false);
const storedExploreSearches = useLocalStorageRef("storedExploreSearches", []);
const eventsStore = useEventsStore();
const { events, status, page_count } = storeToRefs(eventsStore);
const props = defineProps({
  page_size: {
    type: Number,
    default: 10,
  },
});

const exportedEvents = ref([]);

function onPageChange(page) {
  eventsStore.search({
    page: page,
    size: props.page_size,
    query: searchQuery.value,
    searchAttributes: searchAttributes.value,
  });
}
onPageChange(1);

function search() {
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: searchQuery.value,
    searchAttributes: searchAttributes.value,
  });

  if (
    searchQuery.value &&
    !storedExploreSearches.value.includes(searchQuery.value)
  ) {
    storedExploreSearches.value.push(searchQuery.value);
  }
  if (storedExploreSearches.value.length > 10) {
    storedExploreSearches.value.shift();
  }
}

function downloadCurrentPageJson() {
  if (!events.value || !events.value.results) return;

  const payload = {
    query: searchQuery.value,
    search_attributes: searchAttributes.value,
    page_size: props.page_size,
    results_on_page: events.value.results.length,
    total_results: events.value.total,
    took_ms: events.value.took,
    results: events.value.results,
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: "application/json",
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `misp-lite-explore-${Date.now()}.json`;
  a.click();

  URL.revokeObjectURL(url);
}

async function downloadAllResults(format) {
  if (events.value && events.value.total > 1000) {
    if (
      !confirm(`Export ${events.value.total} results? This may take a while.`)
    ) {
      return;
    }
  }

  try {
    if (format === "ndjson") {
      // Stream NDJSON directly from the API to avoid loading everything in memory.
      // Use fetchWrapper.downloadAttachment so auth headers are applied.
      eventsStore.status = { exporting: true };
      const qs = new URLSearchParams({
        query: searchQuery.value,
        searchAttributes: searchAttributes.value,
        format: format,
      }).toString();
      const url = `${import.meta.env.VITE_API_URL}/events/export?${qs}`;
      const res = await fetchWrapper.downloadAttachment(url);
      if (!res.ok)
        throw new Error(`Export failed: ${res.status} ${res.statusText}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const rawChunks = [];
      exportedEvents.value = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        rawChunks.push(chunk);
        buffer += chunk;
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop(); // last partial line stays in buffer
        for (const line of lines) {
          if (!line) continue;
          try {
            const obj = JSON.parse(line);
            exportedEvents.value.push(obj);
          } catch (e) {
            // If a line isn't valid JSON, skip it but keep raw
            console.warn("Failed to parse NDJSON line", e, line);
          }
        }
      }

      if (buffer) {
        try {
          const obj = JSON.parse(buffer);
          exportedEvents.value.push(obj);
          rawChunks.push(buffer);
        } catch (e) {
          // ignore
          console.warn("Failed to parse final NDJSON line", e, buffer);
        }
      }

      // Download raw NDJSON as a file
      const blob = new Blob(rawChunks, { type: "application/x-ndjson" });
      const downloadUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `misp-lite-explore-all-${Date.now()}.ndjson`;
      a.click();
      URL.revokeObjectURL(downloadUrl);

      // Optionally store parsed results in localStorage (be careful with size)
      try {
        const MAX_STORE = 5 * 1024 * 1024; // 5 MB
        const serialized = JSON.stringify(exportedEvents.value);
        if (serialized.length < MAX_STORE) {
          localStorage.setItem("exported_events", serialized);
        } else {
          console.warn("Exported results too large to store in localStorage");
        }
      } catch (e) {
        console.warn("Failed to persist exported events", e);
      }

      eventsStore.status = { exporting: false };
      return;
    }

    // fallback: use existing store export (JSON)
    const results = await eventsStore.export({
      query: searchQuery.value,
      searchAttributes: searchAttributes.value,
      format: format,
    });

    const blobJson = new Blob([JSON.stringify(results, null, 2)], {
      type: "application/json",
    });

    const url = URL.createObjectURL(blobJson);
    const a = document.createElement("a");
    a.href = url;
    a.download = `misp-lite-explore-all-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error(err);
    alert("Failed to export results: " + (err?.message || err));
    eventsStore.status = { exporting: false };
  }
}
</script>

<style>
body {
  margin: 0;
}
</style>

<template>
  <div class="d-flex justify-content-center">
    <div class="w-100" style="max-width: 600px">
      <div class="input-group input-group-lg mb-3">
        <input
          type="text"
          class="form-control"
          list="previous-searches"
          placeholder="Search something (Lucene Query Syntax) ..."
          v-model="searchQuery"
          v-on:keyup.enter="search"
        />

        <datalist id="previous-searches">
          <option v-for="term in storedExploreSearches">{{ term }}</option>
        </datalist>

        <button class="btn btn-primary btn-lg" type="button" @click="search">
          <FontAwesomeIcon :icon="faMagnifyingGlass" />
        </button>
      </div>
      <div class="form-check form-switch mb-3">
        <input
          class="form-check-input"
          type="checkbox"
          id="searchAttributesSwitch"
          v-model="searchAttributes"
          @change="search"
        />
        <label class="form-check-label" for="searchAttributesSwitch"
          >search attributes</label
        >
      </div>
    </div>
  </div>
  <div>
    <div
      v-if="events && events.total > 0"
      class="d-flex justify-content-end mb-2"
    >
      <div class="btn-group">
        <button
          class="btn btn-outline-secondary dropdown-toggle"
          data-bs-toggle="dropdown"
          :disabled="status.exporting"
        >
          <span v-if="status.exporting">
            <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
          </span>
          <span v-else class="ms-2">
            <FontAwesomeIcon :icon="faFileDownload" /> Download
          </span>
        </button>
        <ul class="dropdown-menu dropdown-menu-end">
          <li>
            <button class="dropdown-item" @click="downloadCurrentPageJson">
              Current page (JSON)
            </button>
          </li>
          <li>
            <button class="dropdown-item" @click="downloadAllResults('json')">
              All results (JSON)
            </button>
          </li>
          <li>
            <button class="dropdown-item" @click="downloadAllResults('ndjson')">
              All results (NDJSON)
            </button>
          </li>
        </ul>
      </div>
    </div>
    <div id="results">
      <Spinner v-if="status.loading" />
      <div v-for="result in events.results">
        <div v-if="!searchAttributes">
          <EventResultCard :event="result" :key="result._source.uuid" />
        </div>
        <div v-if="searchAttributes">
          <AttributeResultCard :attribute="result" :key="result._source.uuid" />
        </div>
      </div>
    </div>
    <div v-if="status.error" class="mt-2 w-100 alert alert-danger mt-3 mb-3">
      <ApiError :errors="status.error" />
    </div>
    <div v-if="!events || events.total == 0">
      <p class="text-center mt-2">No results found.</p>
      <p
        v-if="events.timed_out"
        class="mt-2 text-center w-100 alert alert-danger mt-3 mb-3"
      >
        Request timed out.
      </p>
    </div>
    <div v-if="events && events.total > 0">
      <Paginate
        v-if="page_count > 1"
        :page-count="page_count"
        :click-handler="onPageChange"
      />
      <p class="text-center mt-2">
        {{ events.total }} results found in {{ events.took }}ms
      </p>
    </div>
  </div>
</template>
