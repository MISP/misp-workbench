<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useEventsStore, useAttributesStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import ApiError from "@/components/misc/ApiError.vue";
import {
  faFileDownload,
  faMagnifyingGlass,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";
import Paginate from "vuejs-paginate-next";

import { useLocalStorageRef } from "@/helpers";

import AttributeResultCard from "./AttributeResultCard.vue";
import EventResultCard from "./EventResultCard.vue";

const searchQuery = ref("");
const storedExploreSearches = useLocalStorageRef("storedExploreSearches", []);
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const showEvents = ref(true);
const showAttributes = ref(true);

const {
  event_docs,
  status: eventsStatus,
  page_count: eventsPageCount,
} = storeToRefs(eventsStore);
const {
  attribute_docs,
  status: attributesStatus,
  page_count: attributesPageCount,
} = storeToRefs(attributesStore);

const props = defineProps({
  page_size: {
    type: Number,
    default: 5,
  },
});

function onEventsPageChange(page) {
  eventsStore.search({
    page: page,
    size: props.page_size,
    query: searchQuery.value,
  });
}

function onAttributesPageChange(page) {
  attributesStore.search({
    page: page,
    size: props.page_size,
    query: searchQuery.value,
  });
}

function search() {
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: searchQuery.value,
  });

  attributesStore.search({
    page: 1,
    size: props.page_size,
    query: searchQuery.value,
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

async function downloadAllResults(type, format = "json") {
  const eventsStore = useEventsStore();

  try {
    const params = {
      query: searchQuery.value || "",
      format,
    };

    let data;

    if (type === "attributes") {
      data = await attributesStore.export(params);
    } else if (type === "events") {
      data = await eventsStore.export(params);
    } else {
      throw new Error("Invalid type for export");
    }

    if (!data) {
      throw new Error("No data returned from export");
    }

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);

    // filename
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `misp-lite-${type}-${timestamp}.${format}`;

    // trigger download
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();

    // cleanup
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Export failed:", err);
  }
}
</script>

<style>
body {
  margin: 0;
}

.cursor-pointer {
  cursor: pointer;
}

#eventsResults {
  border-left: 4px solid #0d6efd;
  /* blue */
}

#attributesResults {
  border-left: 4px solid #198754;
  /* green */
}
</style>

<template>
  <div class="d-flex justify-content-center">
    <div class="w-100 mb-3" style="max-width: 600px">
      <div class="input-group input-group-lg mb-1">
        <input
          type="text"
          class="form-control"
          list="previous-searches"
          placeholder="Search something ..."
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
      <span class="text-muted fst-italic small"
        >Lucene query syntax supported</span
      >
    </div>
  </div>
  <div>
    <div id="results">
      <div
        id="eventsResults"
        class="card mb-3"
        v-if="event_docs?.results || eventsStatus.error"
      >
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div
            class="d-flex align-items-center cursor-pointer"
            @click="showEvents = !showEvents"
          >
            <div>
              <strong>Events</strong>
            </div>
            <span v-if="event_docs?.total" class="text-muted ms-2">
              ({{ event_docs.total }})
            </span>
          </div>
          <div class="d-flex align-items-center">
            <div
              v-if="attribute_docs && attribute_docs.total > 0"
              class="btn-group me-2"
            >
              <button
                type="button"
                class="btn btn-outline-secondary dropdown-toggle"
                data-bs-toggle="dropdown"
                :disabled="attributesStatus.exporting"
              >
                <span v-if="attributesStatus.exporting">
                  <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
                </span>
                <span v-else class="ms-2">
                  <FontAwesomeIcon :icon="faFileDownload" /> Download
                </span>
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <button
                    class="dropdown-item"
                    @click="downloadAllResults('events', 'json')"
                  >
                    All results (JSON)
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div v-show="showEvents" class="card-body">
          <div v-if="event_docs?.results?.length">
            <EventResultCard
              v-for="result in event_docs.results"
              :key="result._source.uuid"
              :event="result"
              class="mb-2"
            />
            <Paginate
              v-if="eventsPageCount > 1"
              :page-count="eventsPageCount"
              :click-handler="onEventsPageChange"
            />
          </div>
          <div v-if="eventsStatus?.error" class="alert alert-danger mt-3">
            <ApiError :errors="eventsStatus.error" />
          </div>
          <div
            v-if="event_docs && event_docs.total === 0"
            class="text-center text-muted mt-3"
          >
            No events found.
            <div v-if="event_docs.timed_out" class="alert alert-danger mt-2">
              Request timed out.
            </div>
          </div>
        </div>
        <div
          v-if="showEvents && event_docs?.total > 0"
          class="card-footer text-muted text-center"
        >
          <div class="mt-2">
            {{ event_docs.total }} results · {{ event_docs.took }}ms
          </div>
        </div>
      </div>
      <div
        id="attributesResults"
        class="card mb-3"
        v-if="attribute_docs?.results || attributesStatus.error"
      >
        <div
          class="card-header d-flex justify-content-between align-items-center"
        >
          <div
            class="d-flex align-items-center cursor-pointer"
            @click="showAttributes = !showAttributes"
          >
            <div>
              <strong>Attributes</strong>
              <span v-if="attribute_docs?.total" class="text-muted ms-2">
                ({{ attribute_docs.total }})
              </span>
            </div>
          </div>

          <div class="d-flex align-items-center">
            <div
              v-if="attribute_docs && attribute_docs.total > 0"
              class="btn-group me-2"
            >
              <button
                type="button"
                class="btn btn-outline-secondary dropdown-toggle"
                data-bs-toggle="dropdown"
                :disabled="attributesStatus.exporting"
              >
                <span v-if="attributesStatus.exporting">
                  <FontAwesomeIcon :icon="faSpinner" spin class="ms-2" />
                </span>
                <span v-else class="ms-2">
                  <FontAwesomeIcon :icon="faFileDownload" /> Download
                </span>
              </button>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <button
                    class="dropdown-item"
                    @click="downloadAllResults('attributes', 'json')"
                  >
                    All results (JSON)
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
        <div v-show="showAttributes" class="card-body">
          <div v-if="attribute_docs?.results?.length">
            <AttributeResultCard
              v-for="result in attribute_docs.results"
              :key="result._source.uuid"
              :attribute="result"
              class="mb-2"
            />
            <Paginate
              v-if="attributesPageCount > 1"
              :page-count="attributesPageCount"
              :click-handler="onAttributesPageChange"
            />
          </div>
          <div v-if="attributesStatus?.error" class="alert alert-danger mt-3">
            <ApiError :errors="attributesStatus.error" />
          </div>
          <div
            v-if="attribute_docs && attribute_docs.total === 0"
            class="text-center text-muted mt-3"
          >
            No attributes found.
            <div
              v-if="attribute_docs.timed_out"
              class="alert alert-danger mt-2"
            >
              Request timed out.
            </div>
          </div>
        </div>
        <div
          v-if="showAttributes && attribute_docs?.total > 0"
          class="card-footer text-muted text-center"
        >
          <div class="mt-2">
            {{ attribute_docs.total }} results · {{ attribute_docs.took }}ms
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
