<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useLocalStorageRef } from "@/helpers/local-storage";
import {
  useEventsStore,
  useAttributesStore,
  useUserSettingsStore,
} from "@/stores";

import AttributeResultCard from "./AttributeResultCard.vue";
import EventResultCard from "./EventResultCard.vue";
import ExploreSearchBar from "./ExploreSearchBar.vue";
import ExploreSearchHistory from "./ExploreSearchHistory.vue";
import ExploreResultsSection from "./ExploreResultsSection.vue";

const props = defineProps({
  page_size: {
    type: Number,
    default: 5,
  },
});

const searchQuery = ref("");

const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();
const userSettingsStore = useUserSettingsStore();
const { userSettings } = storeToRefs(userSettingsStore);

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

const userRecentSearches = useLocalStorageRef(
  "user_recent_explore_searches",
  [],
);

const storedExploreSearches = computed(
  () => userSettings.value?.explore?.saved_searches || [],
);

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
    !userRecentSearches.value.includes(searchQuery.value) &&
    !storedExploreSearches.value.includes(searchQuery.value)
  ) {
    userRecentSearches.value.push(searchQuery.value);
  }
  if (userRecentSearches.value.length > 10) {
    userRecentSearches.value.shift();
  }
}

function onEventsPageChange(page) {
  eventsStore.search({ page, size: props.page_size, query: searchQuery.value });
}

function onAttributesPageChange(page) {
  attributesStore.search({
    page,
    size: props.page_size,
    query: searchQuery.value,
  });
}

async function downloadAllResults(type, format = "json") {
  try {
    const params = { query: searchQuery.value || "", format };
    let data;
    if (type === "attributes") {
      data = await attributesStore.export(params);
    } else if (type === "events") {
      data = await eventsStore.export(params);
    } else {
      throw new Error("Invalid type for export");
    }
    if (!data) throw new Error("No data returned from export");

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = window.URL.createObjectURL(blob);
    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const filename = `misp-workbench-${type}-${timestamp}.${format}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  } catch (err) {
    console.error("Export failed:", err);
  }
}

function saveSearch(term) {
  userSettingsStore.update("explore", {
    saved_searches: Array.from(new Set([term, ...storedExploreSearches.value])),
  });
  const idx = userRecentSearches.value.findIndex((t) => t === term);
  if (idx !== -1) userRecentSearches.value.splice(idx, 1);
}

function deleteSavedSearch(term) {
  userSettingsStore.update("explore", {
    saved_searches: storedExploreSearches.value.filter((t) => t !== term),
  });
}

function onHistorySelect(term) {
  searchQuery.value = term;
  search();
}

function forgetRecentSearch(term) {
  const idx = userRecentSearches.value.findIndex((t) => t === term);
  if (idx !== -1) userRecentSearches.value.splice(idx, 1);
}
</script>

<style>
body {
  margin: 0;
}

.cursor-pointer {
  cursor: pointer;
}

.text-console {
  font-family: "Courier New", Courier, monospace;
}
</style>

<template>
  <div class="row mb-3 justify-content-center align-items-start">
    <div class="col-auto">
      <ExploreSearchHistory
        :saved-searches="storedExploreSearches"
        :recent-searches="userRecentSearches"
        @select="onHistorySelect"
        @save="saveSearch"
        @delete="deleteSavedSearch"
        @forget="forgetRecentSearch"
      />
    </div>
    <div class="col-12 col-md-6">
      <ExploreSearchBar
        v-model="searchQuery"
        :stored-searches="storedExploreSearches"
        @search="search"
        @save="saveSearch"
      />
    </div>

    <div id="results">
      <ExploreResultsSection
        title="Events"
        :docs="event_docs"
        :status="eventsStatus"
        :page-count="eventsPageCount"
        border-color="#0d6efd"
        @page-change="onEventsPageChange"
        @download="downloadAllResults('events', $event)"
      >
        <EventResultCard
          v-for="result in event_docs.results"
          :key="result._source.uuid"
          :event="result"
          class="mb-2"
        />
      </ExploreResultsSection>

      <ExploreResultsSection
        title="Attributes"
        :docs="attribute_docs"
        :status="attributesStatus"
        :page-count="attributesPageCount"
        border-color="#198754"
        @page-change="onAttributesPageChange"
        @download="downloadAllResults('attributes', $event)"
      >
        <AttributeResultCard
          v-for="result in attribute_docs.results"
          :key="result._source.uuid"
          :attribute="result"
          class="mb-2"
        />
      </ExploreResultsSection>
    </div>
  </div>
</template>
