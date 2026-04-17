<script setup>
import { ref, computed, watch } from "vue";
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
import ExploreTimeRangeFilter from "./ExploreTimeRangeFilter.vue";
import AddHuntModal from "@/components/hunts/AddHuntModal.vue";
import EventsPropertiesModal from "@/components/misc/EventsPropertiesModal.vue";
import AttributesPropertiesModal from "@/components/misc/AttributesPropertiesModal.vue";
import ExploreTimelineChart from "./ExploreTimelineChart.vue";

const props = defineProps({
  page_size: {
    type: Number,
    default: 5,
  },
});

const eventsStore = useEventsStore();
const retentionConfig = ref(null);
eventsStore.retentionStatus().then((config) => {
  retentionConfig.value = config;
});

const searchQuery = ref("");
const activeTimeRange = ref(null);
const huntModalOpen = ref(false);
const activeTab = useLocalStorageRef("explore_active_tab", "events");
const eventsSortBy = useLocalStorageRef("explore_events_sort_by", "@timestamp");
const eventsSortOrder = useLocalStorageRef("explore_events_sort_order", "desc");
const attributesSortBy = useLocalStorageRef(
  "explore_attributes_sort_by",
  "@timestamp",
);
const attributesSortOrder = useLocalStorageRef(
  "explore_attributes_sort_order",
  "desc",
);

const eventsFilters = ref([]);
const attributesFilters = ref([]);

const timelineEventBuckets = ref([]);
const timelineAttributeBuckets = ref([]);
const timelineLoading = ref(false);

function applyFilters(baseQuery, filters) {
  const parts = [
    baseQuery,
    ...filters.map((f) => `${f.field}:"${f.value}"`),
  ].filter(Boolean);
  return parts.join(" AND ");
}

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

function buildQuery() {
  const parts = [];
  if (searchQuery.value) parts.push(searchQuery.value);
  if (activeTimeRange.value) {
    const { from, to } = activeTimeRange.value;
    parts.push(`@timestamp:[${from} TO ${to}]`);
  }
  return parts.join(" AND ");
}

function onTimelineFilterDay(date) {
  activeTimeRange.value = {
    mode: "absolute",
    from: `${date}T00:00:00`,
    to: `${date}T23:59:59`,
  };
  search();
}

async function searchTimeline(query) {
  timelineLoading.value = true;
  const [eventsHist, attributesHist] = await Promise.all([
    eventsStore.histogram({ query, interval: "1d" }),
    attributesStore.histogram({ query, interval: "1d" }),
  ]);
  timelineEventBuckets.value = eventsHist?.buckets ?? [];
  timelineAttributeBuckets.value = attributesHist?.buckets ?? [];
  timelineLoading.value = false;
}

function search() {
  const base = buildQuery();
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(base, eventsFilters.value),
    sort_by: eventsSortBy.value,
    sort_order: eventsSortOrder.value,
  });
  attributesStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(base, attributesFilters.value),
    sort_by: attributesSortBy.value,
    sort_order: attributesSortOrder.value,
  });
  searchTimeline(base);

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

watch(event_docs, (docs) => {
  if (
    activeTab.value === "attributes" &&
    attribute_docs.value?.total === 0 &&
    docs?.total > 0
  ) {
    activeTab.value = "events";
  }
});

watch(attribute_docs, (docs) => {
  if (
    activeTab.value === "events" &&
    event_docs.value?.total === 0 &&
    docs?.total > 0
  ) {
    activeTab.value = "attributes";
  }
});

function onEventsPageChange(page) {
  eventsStore.search({
    page,
    size: props.page_size,
    query: applyFilters(buildQuery(), eventsFilters.value),
    sort_by: eventsSortBy.value,
    sort_order: eventsSortOrder.value,
  });
}

function onAttributesPageChange(page) {
  attributesStore.search({
    page,
    size: props.page_size,
    query: applyFilters(buildQuery(), attributesFilters.value),
    sort_by: attributesSortBy.value,
    sort_order: attributesSortOrder.value,
  });
}

function onEventsSortChange({ sortBy, sortOrder }) {
  eventsSortBy.value = sortBy;
  eventsSortOrder.value = sortOrder;
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(buildQuery(), eventsFilters.value),
    sort_by: sortBy,
    sort_order: sortOrder,
  });
}

function onAttributesSortChange({ sortBy, sortOrder }) {
  attributesSortBy.value = sortBy;
  attributesSortOrder.value = sortOrder;
  attributesStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(buildQuery(), attributesFilters.value),
    sort_by: sortBy,
    sort_order: sortOrder,
  });
}

function onEventsFilterChange(filters) {
  eventsFilters.value = filters;
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(buildQuery(), filters),
    sort_by: eventsSortBy.value,
    sort_order: eventsSortOrder.value,
  });
}

function onAttributesFilterChange(filters) {
  attributesFilters.value = filters;
  attributesStore.search({
    page: 1,
    size: props.page_size,
    query: applyFilters(buildQuery(), filters),
    sort_by: attributesSortBy.value,
    sort_order: attributesSortOrder.value,
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
  <div class="row mb-3 align-items-start">
    <div
      class="d-none d-md-block col-md-auto order-md-1 mb-0"
      style="width: 300px"
    >
      <ExploreSearchHistory
        :saved-searches="storedExploreSearches"
        :recent-searches="userRecentSearches"
        @select="onHistorySelect"
        @save="saveSearch"
        @delete="deleteSavedSearch"
        @forget="forgetRecentSearch"
      />
    </div>
    <div class="col-12 col-md order-1 order-md-2">
      <ExploreSearchBar
        v-model="searchQuery"
        :stored-searches="storedExploreSearches"
        @search="search"
        @save="saveSearch"
        @save-as-hunt="huntModalOpen = true"
      />
    </div>
    <div class="col-12 col-md-auto order-2 order-md-3 mt-2 mt-md-0">
      <ExploreTimeRangeFilter
        :model-value="activeTimeRange"
        @change="
          (r) => {
            activeTimeRange = r;
            search();
          }
        "
      />
    </div>

    <div
      v-if="
        timelineLoading ||
        timelineEventBuckets.length > 0 ||
        timelineAttributeBuckets.length > 0
      "
      class="col-12 mt-3 order-3"
    >
      <ExploreTimelineChart
        :event-buckets="timelineEventBuckets"
        :attribute-buckets="timelineAttributeBuckets"
        :loading="timelineLoading"
        @filter-day="onTimelineFilterDay"
      />
    </div>

    <div id="results" class="col-12 mt-3 order-4">
      <div class="col-12 mx-auto">
        <ul class="nav nav-tabs">
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'events' }"
              @click="activeTab = 'events'"
            >
              Events
              <span
                v-if="event_docs?.total != null"
                class="badge ms-1"
                :class="
                  activeTab === 'events'
                    ? 'text-bg-primary'
                    : 'text-bg-secondary'
                "
              >
                {{ event_docs.total }}
              </span>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'attributes' }"
              @click="activeTab = 'attributes'"
            >
              Attributes
              <span
                v-if="attribute_docs?.total != null"
                class="badge ms-1"
                :class="
                  activeTab === 'attributes'
                    ? 'text-bg-success'
                    : 'text-bg-secondary'
                "
              >
                {{ attribute_docs.total }}
              </span>
            </button>
          </li>
        </ul>

        <div class="border border-top-0 rounded-bottom mb-3">
          <div v-show="activeTab === 'events'">
            <ExploreResultsSection
              title="Events"
              :docs="event_docs"
              :status="eventsStatus"
              :page-count="eventsPageCount"
              :sort-by="eventsSortBy"
              :sort-order="eventsSortOrder"
              :filter-fields="['organisation', 'tags']"
              :visible="activeTab === 'events'"
              @page-change="onEventsPageChange"
              @download="downloadAllResults('events', $event)"
              @sort-change="onEventsSortChange"
              @filter-change="onEventsFilterChange"
            >
              <template #header-extra>
                <EventsPropertiesModal />
              </template>
              <EventResultCard
                v-for="result in event_docs.results"
                :key="result._source.uuid"
                :event="result"
                :retention-config="retentionConfig"
                class="mb-2"
              />
            </ExploreResultsSection>
          </div>

          <div v-show="activeTab === 'attributes'">
            <ExploreResultsSection
              title="Attributes"
              :docs="attribute_docs"
              :status="attributesStatus"
              :page-count="attributesPageCount"
              :sort-by="attributesSortBy"
              :sort-order="attributesSortOrder"
              :filter-fields="['organisation', 'tags', 'type']"
              :visible="activeTab === 'attributes'"
              @page-change="onAttributesPageChange"
              @download="downloadAllResults('attributes', $event)"
              @sort-change="onAttributesSortChange"
              @filter-change="onAttributesFilterChange"
            >
              <template #header-extra>
                <AttributesPropertiesModal />
              </template>
              <AttributeResultCard
                v-for="result in attribute_docs.results"
                :key="result._source.uuid"
                :attribute="result"
                class="mb-2"
              />
            </ExploreResultsSection>
          </div>
        </div>
      </div>
    </div>
  </div>

  <AddHuntModal
    v-if="huntModalOpen"
    :initial-query="buildQuery()"
    @created="huntModalOpen = false"
    @close="huntModalOpen = false"
  />
</template>
