<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from "vue";
import { storeToRefs } from "pinia";
import { useLocalStorageRef } from "@/helpers/local-storage";
import {
  useEventsStore,
  useAttributesStore,
  useUserSettingsStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import ApiError from "@/components/misc/ApiError.vue";
import {
  faCaretDown,
  faCaretUp,
  faFileDownload,
  faFileLines,
  faFloppyDisk,
  faMagnifyingGlass,
  faSpinner,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import Paginate from "vuejs-paginate-next";

import AttributeResultCard from "./AttributeResultCard.vue";
import EventResultCard from "./EventResultCard.vue";
import LuceneQuerySyntaxCheatsheet from "./LuceneQuerySyntaxCheatsheetModal.vue";

const searchQuery = ref("");
const eventsStore = useEventsStore();
const attributesStore = useAttributesStore();

const userSettingsStore = useUserSettingsStore();
const { userSettings } = storeToRefs(userSettingsStore);

const showEvents = ref(true);
const showAttributes = ref(true);

const userRecentSearches = useLocalStorageRef(
  "user_recent_explore_searches",
  [],
);

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

// animated placeholder / focus state
const isFocused = ref(false);
const animatedPlaceholder = ref("Search something (Lucene Query Syntax) ...");

const _examples = [
  "info:banking",
  "type.keyword:ip*",
  'expanded.ip2geo.country_iso_code:"RU"',
  "@timestamp:[2026-01-01 TO *]",
  '"admin@example.com"',
  'tags.name.keyword:"tlp:amber"',
  'uuid:"094cecb9-2bd0-4c15-97f1-21373601b36"',
];

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

let _stopAnim = false;
async function _runAnimatedPlaceholder() {
  const typingDelay = 40;
  const pauseDelay = 2000;
  while (!_stopAnim) {
    // if user is interacting or has typed something, show default and wait
    if (
      isFocused.value ||
      (searchQuery.value && searchQuery.value.length > 0)
    ) {
      animatedPlaceholder.value = "Search something (Lucene Query Syntax) ...";
      await sleep(300);
      continue;
    }

    for (let i = 0; i < _examples.length && !_stopAnim; i++) {
      const s = _examples[i];
      // type
      for (let j = 1; j <= s.length && !_stopAnim; j++) {
        if (
          isFocused.value ||
          (searchQuery.value && searchQuery.value.length > 0)
        )
          break;
        animatedPlaceholder.value = s.slice(0, j);
        await sleep(typingDelay);
      }
      if (
        isFocused.value ||
        (searchQuery.value && searchQuery.value.length > 0)
      )
        break;
      await sleep(pauseDelay);
      // delete
      for (let j = s.length; j >= 0 && !_stopAnim; j--) {
        if (
          isFocused.value ||
          (searchQuery.value && searchQuery.value.length > 0)
        )
          break;
        animatedPlaceholder.value = s.slice(0, j);
        await sleep(typingDelay / 2);
      }
      if (
        isFocused.value ||
        (searchQuery.value && searchQuery.value.length > 0)
      )
        break;
      await sleep(200);
    }
  }
}

onMounted(() => {
  _stopAnim = false;
  _runAnimatedPlaceholder();
});

onUnmounted(() => {
  _stopAnim = true;
});

// if searchQuery changes to non-empty, ensure placeholder resets
watch(searchQuery, (v) => {
  if (v && v.length > 0) animatedPlaceholder.value = "";
});

const storedExploreSearches = computed(
  () => userSettings.value?.explore?.saved_searches || [],
);

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
    !userRecentSearches.value.includes(searchQuery.value) &&
    !storedExploreSearches.value.includes(searchQuery.value)
  ) {
    userRecentSearches.value.push(searchQuery.value);
  }
  if (userRecentSearches.value.length > 10) {
    userRecentSearches.value.shift();
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
    const filename = `misp-workbench-${type}-${timestamp}.${format}`;

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

function saveSearch(term) {
  console.log("saveSearch", term);
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

// saved searches card body collapsed by default
const savedCardOpen = ref(false);

function toggleSavedCard() {
  savedCardOpen.value = !savedCardOpen.value;
}

// detect clicks outside the saved-searches panel to close the card body
const savedPanelRef = ref(null);

function _handleDocumentClick(e) {
  try {
    const el = savedPanelRef.value;
    if (!el) return;
    // if card is open and the click is outside the panel, close it
    if (savedCardOpen.value && !el.contains(e.target)) {
      savedCardOpen.value = false;
    }
  } catch (err) {
    console.error("Error handling document click:", err);
  }
}

onMounted(() => {
  document.addEventListener("click", _handleDocumentClick);
});

onUnmounted(() => {
  document.removeEventListener("click", _handleDocumentClick);
});
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

/* saved searches overlay */
.saved-searches-panel {
  position: fixed;
  z-index: 1;
  /* show on top */
}

.saved-searches-panel .list-group {
  scrollbar-gutter: stable;
}

.saved-searches-panel {
  width: 300px;
}

@media (max-width: 768px) {
  .saved-searches-panel {
    width: 90%;
    left: 5%;
    top: 10rem;
  }
}

.card > .card-body:last-child .list-group-flush > .list-group-item:last-child {
  border-bottom-left-radius: var(--bs-card-border-radius);
  border-bottom-right-radius: var(--bs-card-border-radius);
}

.card-body .list-group-flush:last-of-type .list-group-item:last-child {
  border-bottom-left-radius: var(--bs-card-border-radius);
  border-bottom-right-radius: var(--bs-card-border-radius);
}

.text-console {
  font-family: "Courier New", Courier, monospace;
}
</style>

<template>
  <div class="row mb-3 justify-content-center align-items-start">
    <div class="col-012">
      <div
        class="saved-searches-panel"
        ref="savedPanelRef"
        role="dialog"
        aria-label="saved searches"
      >
        <div class="card">
          <div
            class="card-header saved-searches-header d-flex justify-content-between align-items-center"
            role="button"
            tabindex="0"
            @click="toggleSavedCard"
            @keydown.enter.prevent="toggleSavedCard"
            @keydown.space.prevent="toggleSavedCard"
          >
            <div>
              <strong>search history</strong>
              <span class="text-muted ms-2"
                >({{
                  storedExploreSearches.length + userRecentSearches.length
                }})</span
              >
            </div>

            <FontAwesomeIcon
              :icon="faCaretDown"
              class="text-muted transition"
              :class="{ 'rotate-180': savedCardOpen }"
            />
          </div>

          <div class="card-body p-0" v-show="savedCardOpen">
            <ul
              class="list-group list-group-flush"
              style="max-height: 60vh; overflow: auto"
              v-if="storedExploreSearches.length > 0"
            >
              <li
                v-for="(term, idx) in storedExploreSearches"
                :key="term + idx"
                class="list-group-item d-flex justify-content-between align-items-center"
              >
                <div
                  class="text-truncate cursor-pointer text-console"
                  :title="term"
                  style="max-width: 220px"
                  @click="((searchQuery = term), search())"
                >
                  {{ term }}
                </div>

                <div class="btn-group btn-group-sm">
                  <button
                    class="btn text-secondary"
                    @click="deleteSavedSearch(term)"
                  >
                    <FontAwesomeIcon :icon="faXmark" />
                  </button>
                </div>
              </li>
              <li
                v-for="(term, idx) in userRecentSearches"
                :key="term + idx"
                class="list-group-item d-flex justify-content-between align-items-center"
              >
                <div
                  class="text-truncate cursor-pointer text-console"
                  :title="term"
                  style="max-width: 220px"
                  @click="((searchQuery = term), search())"
                >
                  {{ term }}
                </div>
                <div class="btn-group btn-group-sm">
                  <button class="btn text-secondary" @click="saveSearch(term)">
                    <FontAwesomeIcon :icon="faFloppyDisk" />
                  </button>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
    <div class="col-12 col-md-6">
      <div class="w-100">
        <div class="input-group input-group mb-1">
          <button
            class="btn btn-outline-secondary btn"
            type="button"
            @click="saveSearch(searchQuery)"
          >
            <FontAwesomeIcon :icon="faFloppyDisk" />
          </button>
          <input
            type="text"
            class="form-control text-console"
            list="previous-searches"
            :placeholder="animatedPlaceholder"
            @focus="isFocused = true"
            @blur="isFocused = false"
            v-model="searchQuery"
            v-on:keyup.enter="search"
          />
          <datalist id="previous-searches">
            <option v-for="term in storedExploreSearches">{{ term }}</option>
          </datalist>
          <button class="btn btn-primary btn" type="button" @click="search">
            <FontAwesomeIcon :icon="faMagnifyingGlass" />
          </button>
        </div>
        <span class="text-muted fst-italic small d-flex align-items-center">
          Lucene query syntax supported
          <button
            type="button"
            class="btn btn-sm d-flex align-items-center"
            data-bs-toggle="modal"
            data-bs-target="#luceneQuerySyntaxCheatsheetModal"
            alt="Lucene Query Syntax Cheatsheet"
          >
            <FontAwesomeIcon :icon="faFileLines" class="ms-1 cursor-pointer" />
          </button>
        </span>
        <LuceneQuerySyntaxCheatsheet />
      </div>
    </div>

    <div id="results">
      <div
        id="eventsResults"
        class="card mb-3 col-12 col-md-8 mx-auto"
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
              <div>
                <strong>Events</strong>
                <span v-if="event_docs?.total" class="text-muted ms-2">
                  ({{ event_docs.total }})
                </span>
                <span class="ms-2" aria-hidden="true">
                  <span v-if="showEvents">
                    <FontAwesomeIcon :icon="faCaretUp" class="ms-2" />
                  </span>
                  <span v-else>
                    <FontAwesomeIcon :icon="faCaretDown" class="ms-2" />
                  </span>
                </span>
              </div>
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
        class="card mb-3 col-12 col-md-8 mx-auto"
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
              <span class="ms-2" aria-hidden="true">
                <span v-if="showAttributes">
                  <FontAwesomeIcon :icon="faCaretUp" class="ms-2" />
                </span>
                <span v-else>
                  <FontAwesomeIcon :icon="faCaretDown" class="ms-2" />
                </span>
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
