<script setup>
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";
import { useRemoteMISPEventsStore } from "@/stores";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faDownload, faEye } from "@fortawesome/free-solid-svg-icons";

const remoteMISPEventsStore = useRemoteMISPEventsStore();

const props = defineProps(["server"]);
const { remote_events, page, size, status } = storeToRefs(
  remoteMISPEventsStore,
);

remoteMISPEventsStore.get_remote_server_events_index(props.server.id);

function pullRemoteMISPEvent(event_uuid) {
  remoteMISPEventsStore.pull_remote_misp_event(props.server.id, event_uuid);
}

function handleNextPage() {
  page.value = page.value + 1;
  remote_events.value = [];
  remoteMISPEventsStore.get_remote_server_events_index(props.server.id, {
    page: page.value,
    limit: size.value,
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
  });
}
</script>

<template>
  <div class="mb-3">
    <div class="table-responsive-sm">
      <table class="table table-striped">
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
