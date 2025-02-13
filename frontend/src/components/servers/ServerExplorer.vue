<script setup>
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";
import { useRemoteMISPEventsStore } from "@/stores";
import { reactive, computed } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faDownload,
  faEye,
  faMagnifyingGlass,
} from "@fortawesome/free-solid-svg-icons";
import ThreatLevelSelect from "../enums/ThreatLevelSelect.vue";
import AnalysisLevelSelect from "../enums/AnalysisLevelSelect.vue";
import Datepicker from "@/components/misc/Datepicker.vue";

const remoteMISPEventsStore = useRemoteMISPEventsStore();

const props = defineProps(["server"]);
const { remote_events, page, size, status } = storeToRefs(
  remoteMISPEventsStore,
);

remoteMISPEventsStore.get_remote_server_events_index(props.server.id);

const filters = reactive({
  attribute_value: "",
  event_uuid: "",
  organisation: "",
  event_info: "",
  tags: "",
  threat_level: "",
  analysis_level: "",
  timestamp_from: "",
  timestamp_to: "",
});

const activeFilters = computed(() => {
  return Object.values(filters).filter((f) => f).length;
});

const applyFilters = () => {
  console.log("Applying filters:", filters);
};

const resetFilters = () => {
  Object.assign(filters, {
    attribute_value: "",
    event_uuid: "",
    organisation: "",
    event_info: "",
    tags: "",
    threat_level: "",
    analysis_level: "",
    timestamp_from: "",
    timestamp_to: "",
  });
  remoteMISPEventsStore.get_remote_server_events_index(props.server.id);
};

function pullRemoteMISPEvent(event_uuid) {
  remoteMISPEventsStore.pull_remote_misp_event(props.server.id, event_uuid);
}

function handleNextPage() {
  page.value = page.value + 1;
  remote_events.value = [];
  remoteMISPEventsStore.get_remote_server_events_index(props.server.id, {
    page: page.value,
    limit: size.value,
    ...filters,
  });
}

function handlePrevPage() {
  if (page.value == 0) {
    return;
  }
  remote_events.value = [];
  page.value = page.value - 1;
  remoteMISPEventsStore.get_remote_server_events_index(props.server.id, {
    page: page.value,
    limit: size.value,
    ...filters,
  });
}

function searchRemoteMISPEvents() {
  remote_events.value = [];
  remoteMISPEventsStore.get_remote_server_events_index(props.server.id, {
    page: page.value,
    limit: size.value,
    ...filters,
  });
}
</script>

<style>
.card-title {
  margin-bottom: 0 !important;
}
</style>

<template>
  <h4 class="text-muted text-center">
    Remote MISP events from <i>{{ server.name }}</i>
  </h4>
  <nav class="navbar">
    <div class="card">
      <div class="card-title">
        <button
          class="btn btn-link text-decoration-none"
          data-bs-toggle="collapse"
          data-bs-target="#searchFilters"
        >
          <FontAwesomeIcon :icon="faMagnifyingGlass" /> Search Filters
          <span
            class="badge rounded-pill badge-notification bg-secondary"
            v-if="activeFilters"
            >{{ activeFilters }}</span
          >
        </button>
      </div>
      <div id="searchFilters" class="collapse p-3">
        <form @submit.prevent="applyFilters">
          <div class="row g-3">
            <div class="col-md-4">
              <label class="form-label">event info</label>
              <input
                v-model="filters.event_info"
                class="form-control"
                type="text"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">event UUID</label>
              <input
                v-model="filters.event_uuid"
                class="form-control"
                type="text"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">organization</label>
              <input
                v-model="filters.organisation"
                class="form-control"
                type="text"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">attribute value</label>
              <input
                v-model="filters.attribute_value"
                class="form-control"
                type="text"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">tags</label>
              <input v-model="filters.tags" class="form-control" type="text" />
            </div>
            <div class="col-md-4">
              <label class="form-label">threat level</label>
              <ThreatLevelSelect
                v-model="filters.threat_level"
                name="filters.threat_level"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">analysis level</label>
              <AnalysisLevelSelect
                v-model="filters.analysis_level"
                name="filters.analysis_level"
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">timestamp from</label>
              <Datepicker
                v-model="filters.timestamp_from"
                name="filters.timestamp_from"
                altFormat="Z"
                dateFormat="U"
                enableTime
              />
            </div>
            <div class="col-md-4">
              <label class="form-label">timestamp until</label>
              <Datepicker
                v-model="filters.timestamp_to"
                name="filters.timestamp_to"
                altFormat="Z"
                dateFormat="U"
                enableTime
              />
            </div>
          </div>
          <div class="mt-3 text-end">
            <button
              type="button"
              class="btn btn-secondary me-2"
              @click="resetFilters"
              data-bs-toggle="collapse"
              data-bs-target="#searchFilters"
            >
              Reset
            </button>
            <button
              type="submit"
              class="btn btn-primary"
              @click="searchRemoteMISPEvents"
            >
              Search
            </button>
          </div>
        </form>
      </div>
    </div>
  </nav>
  <div class="mb-3">
    <div class="table-responsive-sm">
      <table class="table table-striped table-hover">
        <thead>
          <tr>
            <th scope="col">uuid</th>
            <th scope="col">info</th>
            <th scope="col">timestamp</th>
            <th scope="col">organisation</th>
            <th scope="col" class="d-none d-sm-table-cell">tags</th>
            <th scope="col" width="20%" class="text-end">actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="event in remote_events">
            <td>{{ event.uuid }}</td>
            <td>{{ event.info }}</td>
            <td>
              <Timestamp :timestamp="event.timestamp" />
            </td>
            <td>{{ event.Org.name }}</td>
            <td>
              <TagsIndex :tags="event.EventTag" />
            </td>
            <td>
              <div class="text-end">
                <div
                  class="flex-wrap btn-group"
                  aria-label="Remote Event Actions"
                >
                  <RouterLink
                    :to="`/servers/explore/${server.id}/events/${event.uuid}`"
                    class="btn btn-outline-primary"
                  >
                    <FontAwesomeIcon :icon="faEye" />
                  </RouterLink>
                  <button
                    type="button"
                    class="btn btn-outline-primary"
                    data-placement="top"
                    title="Pull Remote Event"
                    @click="pullRemoteMISPEvent(event.uuid)"
                  >
                    <FontAwesomeIcon :icon="faDownload" />
                  </button>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="text-center">
        <Spinner v-if="status.loading" />
      </div>
    </div>
  </div>
  <Pagination
    @nextPageClick="handleNextPage()"
    @prevPageClick="handlePrevPage()"
    :currentPage="page"
    :hasPrevPage="page > 0"
    :hasNextPage="remote_events.length >= size"
  />
</template>
