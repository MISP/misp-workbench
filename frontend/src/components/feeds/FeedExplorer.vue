<script setup>
import { storeToRefs } from "pinia";
import { useFeedEventsStore, useToastsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Pagination from "@/components/misc/Pagination.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import ApiError from "@/components/misc/ApiError.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faDownload, faEye } from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["feed"]);

const feedEventsStore = useFeedEventsStore();
const toastsStore = useToastsStore();
const { feed_events, page, size, total, total_filtered, status } =
  storeToRefs(feedEventsStore);

feedEventsStore.get_feed_events(props.feed.id);

function fetchFeedEvent(event_uuid) {
  feedEventsStore.fetch_feed_event(props.feed.id, event_uuid).then(() => {
    toastsStore.push("Feed event fetch enqueued.");
  });
}

function handleNextPage() {
  page.value = page.value + 1;
  feedEventsStore.get_feed_events(props.feed.id, { page: page.value });
}

function handlePrevPage() {
  if (page.value === 0) return;
  page.value = page.value - 1;
  feedEventsStore.get_feed_events(props.feed.id, { page: page.value });
}
</script>

<template>
  <h4 class="text-muted text-center">
    MISP feed events from <i>{{ feed.name }}</i>
  </h4>
  <div
    v-if="!status.loading && total_filtered !== undefined"
    class="mb-2 text-muted small"
  >
    Showing {{ total_filtered }} events ({{ total }} total in feed)
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th scope="col">uuid</th>
          <th scope="col">info</th>
          <th scope="col">timestamp</th>
          <th scope="col">organisation</th>
          <th scope="col" class="d-none d-sm-table-cell">tags</th>
          <th scope="col" width="15%" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="event in feed_events" :key="event.uuid">
          <td class="text-truncate" style="max-width: 120px">
            {{ event.uuid }}
          </td>
          <td>{{ event.info }}</td>
          <td>
            <Timestamp :timestamp="event.timestamp" />
          </td>
          <td>{{ event.Orgc?.name }}</td>
          <td class="d-none d-sm-table-cell">
            <TagsIndex :tags="event.Tag || []" />
          </td>
          <td>
            <div class="text-end">
              <div class="flex-wrap btn-group" aria-label="Feed Event Actions">
                <RouterLink
                  :to="`/feeds/explore/${feed.id}/events/${event.uuid}`"
                  class="btn btn-outline-primary btn-sm"
                  title="Preview event"
                >
                  <FontAwesomeIcon :icon="faEye" />
                </RouterLink>
                <button
                  type="button"
                  class="btn btn-outline-primary btn-sm"
                  title="Fetch event to local"
                  @click="fetchFeedEvent(event.uuid)"
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
    <div
      v-if="status.error"
      class="w-100 alert alert-danger mt-3 mb-3 text-center"
    >
      <ApiError :errors="status.error" />
    </div>
  </div>
  <Pagination
    @nextPageClick="handleNextPage()"
    @prevPageClick="handlePrevPage()"
    :currentPage="page"
    :hasPrevPage="page > 0"
    :hasNextPage="feed_events.length >= size"
  />
</template>
