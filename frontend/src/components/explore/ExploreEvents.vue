<script setup>
import { ref } from "vue";
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import Spinner from "@/components/misc/Spinner.vue";
import ApiError from "@/components/misc/ApiError.vue";
import { faMagnifyingGlass } from "@fortawesome/free-solid-svg-icons";
import Paginate from "vuejs-paginate-next";

const searchQuery = ref("");
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
  });
}
onPageChange(1);

function search() {
  eventsStore.search({
    page: 1,
    size: props.page_size,
    query: searchQuery.value,
  });
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
          placeholder="Search something (Lucene Query Syntax) ..."
          v-model="searchQuery"
          v-on:keyup.enter="search"
        />
        <button class="btn btn-primary btn-lg" type="button" @click="search">
          <FontAwesomeIcon :icon="faMagnifyingGlass" />
        </button>
      </div>
    </div>
  </div>
  <div>
    <div id="results">
      <Spinner v-if="status.loading" />
      <div v-for="event in events.results">
        <div>{{ event._source.info }}</div>
      </div>
    </div>
    <div v-if="status.error" class="w-100 alert alert-danger mt-3 mb-3">
      <ApiError :errors="status.error" />
    </div>
    <div v-if="!events || events.total == 0">
      <p class="text-center">No results found</p>
    </div>
    <div v-if="events && events.total > 0">
      <Paginate
        v-if="page_count > 1"
        :page-count="page_count"
        :click-handler="onPageChange"
      />
      <p class="text-center">{{ events.total }} results found.</p>
    </div>
  </div>
</template>
