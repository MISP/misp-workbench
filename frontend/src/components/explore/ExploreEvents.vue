<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import Spinner from "@/components/misc/Spinner.vue";
import ApiError from "@/components/misc/ApiError.vue";
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";
import Paginate from "vuejs-paginate-next";

import { useLocalStorageRef } from "@/helpers";

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
