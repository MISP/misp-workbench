<script setup>
import { ref, computed, watch, onMounted } from "vue";
import { useRoute } from "vue-router";
import { storeToRefs } from "pinia";
import { useLocalStorageRef } from "@/helpers/local-storage";
import {
  useEventsStore,
  useAttributesStore,
  useCorrelationsStore,
  useUserSettingsStore,
  useIndicatorsStore,
  useToastsStore,
} from "@/stores";

import AttributeResultCard from "./AttributeResultCard.vue";
import EventResultCard from "./EventResultCard.vue";
import CorrelationResultCard from "./CorrelationResultCard.vue";
import IndicatorResultCard from "./IndicatorResultCard.vue";
import ExploreSearchBar from "./ExploreSearchBar.vue";
import ExploreSearchHistory from "./ExploreSearchHistory.vue";
import ExploreResultsSection from "./ExploreResultsSection.vue";
import ExploreTimeRangeFilter from "./ExploreTimeRangeFilter.vue";
import {
  DEFAULT_TIME_RANGE,
  timeRangeFromQuery,
} from "@/helpers/explore-time-range";
import AddHuntModal from "@/components/hunts/AddHuntModal.vue";
import AddExportModal from "@/components/exports/AddExportModal.vue";
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
const route = useRoute();
// From the link that opened the page (?range=all, or ?from=&to=), else the
// last 30 days. null is All time.
const routeTimeRange = timeRangeFromQuery(route.query);
const activeTimeRange = ref(
  routeTimeRange === undefined ? { ...DEFAULT_TIME_RANGE } : routeTimeRange,
);
const huntModalOpen = ref(false);
const exportModalOpen = ref(false);
const exportModalQuery = ref("");
const exportModalTarget = ref("attributes");
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
const correlationsSortBy = useLocalStorageRef(
  "explore_correlations_sort_by",
  "@timestamp",
);
const correlationsSortOrder = useLocalStorageRef(
  "explore_correlations_sort_order",
  "desc",
);
const includeDeleted = useLocalStorageRef("explore_include_deleted", false);
const indicatorsSortBy = useLocalStorageRef(
  "explore_indicators_sort_by",
  "score",
);
const INDICATOR_SORT_FIELDS = [
  { value: "score", label: "Score" },
  { value: "last_seen", label: "Last seen" },
  { value: "event_count", label: "Events" },
  { value: "first_seen", label: "First seen" },
];

// The page each tab shows: a refresh after a delete stays on it.
const eventsPage = ref(1);
const attributesPage = ref(1);
const correlationsPage = ref(1);
const indicatorsPage = ref(1);

const eventsFilters = ref([]);
const attributesFilters = ref([]);

const timelineEventBuckets = ref([]);
const timelineAttributeBuckets = ref([]);
const timelineCorrelationBuckets = ref([]);
const timelineLoading = ref(false);

function applyFilters(baseQuery, filters) {
  const parts = [
    baseQuery,
    ...filters.map((f) => `${f.field}:"${f.value}"`),
  ].filter(Boolean);
  return parts.join(" AND ");
}

const attributesStore = useAttributesStore();
const correlationsStore = useCorrelationsStore();
const indicatorsStore = useIndicatorsStore();
const userSettingsStore = useUserSettingsStore();
const toastsStore = useToastsStore();
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
const {
  correlation_docs,
  status: correlationsStatus,
  page_count: correlationsPageCount,
} = storeToRefs(correlationsStore);
const {
  explore_docs: indicator_docs,
  exploreStatus: indicatorsStatus,
  explore_page_count: indicatorsPageCount,
} = storeToRefs(indicatorsStore);

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
  return parts.length ? parts.join(" AND ") : "*";
}

// Epoch seconds for a time range bound: "now", "now-30d" or a date.
const UNIT_SECONDS = {
  s: 1,
  m: 60,
  h: 3600,
  d: 86400,
  w: 604800,
  M: 2592000,
  y: 31536000,
};
function toEpochSeconds(value) {
  const relative = /^now(?:-(\d+)([smhdwMy]))?$/.exec(value);
  if (relative) {
    const ago = Number(relative[1] || 0) * UNIT_SECONDS[relative[2] || "s"];
    return Math.floor(Date.now() / 1000) - ago;
  }
  const time = Date.parse(value);
  return Number.isNaN(time) ? null : Math.floor(time / 1000);
}

// Indicators have no @timestamp: the time range applies to when they were
// last seen, which is stored as epoch seconds.
function buildIndicatorQuery() {
  const parts = [];
  if (searchQuery.value) parts.push(`(${searchQuery.value})`);
  if (activeTimeRange.value) {
    const from = toEpochSeconds(activeTimeRange.value.from);
    const to = toEpochSeconds(activeTimeRange.value.to);
    if (from !== null && to !== null)
      parts.push(`last_seen:[${from} TO ${to}]`);
  }
  return parts.length ? parts.join(" AND ") : "*";
}

function searchIndicators(page = 1) {
  indicatorsPage.value = page;
  return indicatorsStore.exploreSearch({
    query: buildIndicatorQuery(),
    page,
    size: props.page_size,
    sort: indicatorsSortBy.value,
  });
}

function onIndicatorsSortChange({ sortBy }) {
  indicatorsSortBy.value = sortBy;
  searchIndicators();
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
  const histogramParams = {
    query,
    interval: "1d",
    include_deleted: includeDeleted.value,
  };
  const [eventsHist, attributesHist, correlationsHist] = await Promise.all([
    eventsStore.histogram(histogramParams),
    attributesStore.histogram(histogramParams),
    correlationsStore.histogram({ query, interval: "1d" }),
  ]);
  timelineEventBuckets.value = eventsHist?.buckets ?? [];
  timelineAttributeBuckets.value = attributesHist?.buckets ?? [];
  timelineCorrelationBuckets.value = correlationsHist?.buckets ?? [];
  timelineLoading.value = false;
}

function searchEvents(page = 1) {
  eventsPage.value = page;
  return eventsStore.search({
    page,
    size: props.page_size,
    query: applyFilters(buildQuery(), eventsFilters.value),
    sort_by: eventsSortBy.value,
    sort_order: eventsSortOrder.value,
    include_deleted: includeDeleted.value,
  });
}

function searchAttributes(page = 1) {
  attributesPage.value = page;
  return attributesStore.search({
    page,
    size: props.page_size,
    query: applyFilters(buildQuery(), attributesFilters.value),
    sort_by: attributesSortBy.value,
    sort_order: attributesSortOrder.value,
    include_deleted: includeDeleted.value,
  });
}

function searchCorrelations(page = 1) {
  correlationsPage.value = page;
  return correlationsStore.search({
    page,
    size: props.page_size,
    query: buildQuery(),
    sort_by: correlationsSortBy.value,
    sort_order: correlationsSortOrder.value,
  });
}

function search() {
  autoFocusPending.value = true;
  searchEvents();
  searchAttributes();
  searchCorrelations();
  searchIndicators();
  searchTimeline(buildQuery());

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

// Tab order as rendered, which is also the order preferred when falling back.
const TABS = ["events", "attributes", "indicators", "correlations"];

function tabTotal(tab) {
  if (tab === "events") return event_docs.value?.total;
  if (tab === "attributes") return attribute_docs.value?.total;
  if (tab === "indicators") return indicator_docs.value?.total;
  return correlation_docs.value?.total;
}

// Set for a new search, cleared once the tab has been chosen. Without it the
// active tab would be second-guessed on every store update -- including the
// user deliberately opening an empty tab to look at its filters.
const autoFocusPending = ref(false);

const searchSettled = computed(
  () =>
    !eventsStatus.value?.loading &&
    !attributesStatus.value?.loading &&
    !indicatorsStatus.value?.loading &&
    !correlationsStatus.value?.loading,
);

/**
 * After a search, land on the first tab that actually has results.
 *
 * Searching a bare indicator value is the common case and it matches
 * attributes, not events -- an event does not carry the value in its own
 * fields. Leaving the user on "Events 0" next to "Attributes 3" makes the
 * platform look like it found nothing.
 *
 * Waits for all three searches to settle rather than reacting to whichever
 * returns first: they are dispatched together, so an early responder would
 * otherwise decide the tab while comparing against the previous search's
 * totals.
 */
watch(
  [searchSettled, event_docs, attribute_docs, indicator_docs, correlation_docs],
  () => {
    if (!autoFocusPending.value || !searchSettled.value) return;
    autoFocusPending.value = false;

    // A tab with results is never taken away from the user.
    if (tabTotal(activeTab.value) > 0) return;

    const firstWithResults = TABS.find((tab) => tabTotal(tab) > 0);
    // Nothing matched anywhere: stay put rather than shuffling through three
    // empty tabs.
    if (firstWithResults) activeTab.value = firstWithResults;
  },
);

function onEventsSortChange({ sortBy, sortOrder }) {
  eventsSortBy.value = sortBy;
  eventsSortOrder.value = sortOrder;
  searchEvents();
}

function onAttributesSortChange({ sortBy, sortOrder }) {
  attributesSortBy.value = sortBy;
  attributesSortOrder.value = sortOrder;
  searchAttributes();
}

function onCorrelationsSortChange({ sortBy, sortOrder }) {
  correlationsSortBy.value = sortBy;
  correlationsSortOrder.value = sortOrder;
  searchCorrelations();
}

function onEventsFilterChange(filters) {
  eventsFilters.value = filters;
  searchEvents();
}

function onAttributesFilterChange(filters) {
  attributesFilters.value = filters;
  searchAttributes();
}

/**
 * Search a tab again on the page it shows; if that page is now past the end
 * (the deleted event was the last thing on it), on the last one left.
 */
async function refreshPage(searchTab, page, docs) {
  await searchTab(page.value);
  const total = docs.value?.total ?? 0;
  if (page.value > 1 && !docs.value?.results?.length && total > 0) {
    await searchTab(Math.ceil(total / props.page_size));
  }
}

/**
 * After an event is deleted from its card, show the results without it:
 * the API has already left it (and its attributes, objects and
 * correlations) out of searches. With deleted results included it stays,
 * marked deleted. Unlike a new search, the tab and pages are kept.
 */
function onEventDeleted({ force } = {}) {
  toastsStore.push(
    force ? "Event permanently deleted." : "Event deleted.",
    "success",
  );
  refreshPage(searchEvents, eventsPage, event_docs);
  refreshPage(searchAttributes, attributesPage, attribute_docs);
  refreshPage(searchCorrelations, correlationsPage, correlation_docs);
  refreshPage(searchIndicators, indicatorsPage, indicator_docs);
  searchTimeline(buildQuery());
}

async function downloadAllResults(type, format = "json") {
  try {
    const params = {
      query: searchQuery.value || "",
      format,
      include_deleted: includeDeleted.value,
    };
    let data;
    if (type === "attributes") {
      data = await attributesStore.export(params);
    } else if (type === "events") {
      data = await eventsStore.export(params);
    } else if (type === "correlations") {
      data = correlation_docs.value?.results ?? [];
    } else if (type === "indicators") {
      data = await indicatorsStore.exportAll(buildIndicatorQuery());
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

function openExportModal(type) {
  const filters =
    type === "events" ? eventsFilters.value : attributesFilters.value;
  exportModalQuery.value = applyFilters(buildQuery(), filters);
  exportModalTarget.value = type;
  exportModalOpen.value = true;
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

// ?q= searches and ?tab=indicators opens a tab: links (a detection profile's
// pivot, the quick switcher) land here with them, on this page or another.
// ?range=all searches all time: a self-contained query (a profile's carries
// its own age rule, a feed's events span years) mustn't be cut to the last
// 30 days. ?from=now-90d&to=now (or dates) sets a range.
function applyRouteQuery({ initial = false } = {}) {
  if (TABS.includes(route.query.tab)) {
    activeTab.value = route.query.tab;
  }
  const range = timeRangeFromQuery(route.query);
  if (range !== undefined) {
    activeTimeRange.value = range;
  }
  const initialQuery = route.query.q;
  if (typeof initialQuery === "string" && initialQuery.length > 0) {
    searchQuery.value = initialQuery;
    search();
  } else if (initial || range !== undefined) {
    search();
  }
}
// One search on arrival, with the link's range already applied: searching
// first with the default range raced the link's search, and whichever
// answered last was shown.
onMounted(() => applyRouteQuery({ initial: true }));
watch(
  () => [
    route.query.q,
    route.query.tab,
    route.query.range,
    route.query.from,
    route.query.to,
  ],
  () => applyRouteQuery(),
);
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
      <div class="form-check form-switch mt-2">
        <input
          class="form-check-input"
          type="checkbox"
          id="includeDeletedToggle"
          v-model="includeDeleted"
          @change="search"
        />
        <label
          class="form-check-label small text-muted"
          for="includeDeletedToggle"
          title="Include soft-deleted events and attributes in results"
        >
          Include deleted
        </label>
      </div>
    </div>

    <div
      v-if="
        timelineLoading ||
        timelineEventBuckets.length > 0 ||
        timelineAttributeBuckets.length > 0 ||
        timelineCorrelationBuckets.length > 0
      "
      class="col-12 mt-3 order-3"
    >
      <ExploreTimelineChart
        :event-buckets="timelineEventBuckets"
        :attribute-buckets="timelineAttributeBuckets"
        :correlation-buckets="timelineCorrelationBuckets"
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
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'indicators' }"
              @click="activeTab = 'indicators'"
            >
              Indicators
              <span
                v-if="indicator_docs?.total != null"
                class="badge ms-1"
                :class="
                  activeTab === 'indicators'
                    ? 'text-bg-info'
                    : 'text-bg-secondary'
                "
              >
                {{ indicator_docs.total }}
              </span>
            </button>
          </li>
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'correlations' }"
              @click="activeTab = 'correlations'"
            >
              Correlations
              <span
                v-if="correlation_docs?.total != null"
                class="badge ms-1"
                :class="
                  activeTab === 'correlations'
                    ? 'text-bg-warning'
                    : 'text-bg-secondary'
                "
              >
                {{ correlation_docs.total }}
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
              :exportable="true"
              :page="eventsPage"
              @page-change="searchEvents"
              @download="downloadAllResults('events', $event)"
              @save-export="openExportModal('events')"
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
                @event-deleted="onEventDeleted"
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
              :exportable="true"
              :page="attributesPage"
              @page-change="searchAttributes"
              @download="downloadAllResults('attributes', $event)"
              @save-export="openExportModal('attributes')"
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

          <div v-show="activeTab === 'indicators'">
            <ExploreResultsSection
              title="Indicators"
              :docs="indicator_docs"
              :status="indicatorsStatus"
              :page-count="indicatorsPageCount"
              :sort-by="indicatorsSortBy"
              sort-order="desc"
              :sort-fields="INDICATOR_SORT_FIELDS"
              :sort-order-toggle="false"
              :filter-fields="[]"
              :visible="activeTab === 'indicators'"
              :page="indicatorsPage"
              @page-change="searchIndicators"
              @download="downloadAllResults('indicators', $event)"
              @sort-change="onIndicatorsSortChange"
            >
              <IndicatorResultCard
                v-for="result in indicator_docs?.results"
                :key="result._id"
                :indicator="result"
                class="mb-2"
              />
            </ExploreResultsSection>
          </div>

          <div v-show="activeTab === 'correlations'">
            <ExploreResultsSection
              title="Correlations"
              :docs="correlation_docs"
              :status="correlationsStatus"
              :page-count="correlationsPageCount"
              :sort-by="correlationsSortBy"
              :sort-order="correlationsSortOrder"
              :filter-fields="[]"
              :visible="activeTab === 'correlations'"
              :page="correlationsPage"
              @page-change="searchCorrelations"
              @download="downloadAllResults('correlations', $event)"
              @sort-change="onCorrelationsSortChange"
            >
              <CorrelationResultCard
                v-for="result in correlation_docs?.results"
                :key="result._id"
                :correlation="result"
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

  <AddExportModal
    v-if="exportModalOpen"
    :initial-query="exportModalQuery"
    :initial-index-target="exportModalTarget"
    @created="exportModalOpen = false"
    @close="exportModalOpen = false"
  />
</template>
