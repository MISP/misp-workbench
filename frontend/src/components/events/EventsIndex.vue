<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import { RouterLink } from "vue-router";
import Spinner from "@/components/misc/Spinner.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import Paginate from "vuejs-paginate-next";
const eventsStore = useEventsStore();
const { page_count, events, status } = storeToRefs(eventsStore);

const props = defineProps(["page_size"]);

function onPageChange(page) {
  eventsStore.get({
    page: page,
    size: props.page_size,
    deleted: false,
  });
}
onPageChange(1);

function handleEventDeleted() {
  // TODO FIXME: resets the page to 1 and reloads the events, not the best way to do this, reload current page
  onPageChange(1);
}
</script>

<style scoped>
.eventInfoColumn {
  width: 50%;
  /* white-space: nowrap; */
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn-toolbar {
  flex-wrap: nowrap !important;
}
</style>

<template>
  <div v-if="status.error" class="text-danger">
    Error loading events: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">id</th>
          <th scope="col" class="eventInfoColumn">info</th>
          <th scope="col">tags</th>
          <th scope="col">date</th>
          <th scope="col" class="d-none d-sm-table-cell">distribution</th>
          <th scope="col" width="20%" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="event.id" v-for="event in events.items">
          <td>
            <RouterLink :to="`/events/${event.id}`">{{ event.id }}</RouterLink>
          </td>
          <td class="eventInfoColumn text-start">{{ event.info }}</td>
          <td>
            <TagsIndex :tags="event.tags" />
          </td>
          <td>{{ event.date }}</td>
          <td class="d-none d-sm-table-cell">
            <DistributionLevel :distribution_level_id="event.distribution" />
          </td>
          <td class="text-end">
            <div class="btn-toolbar float-end" role="toolbar">
              <div
                class="flex-wrap"
                :class="{
                  'btn-group-vertical': $isMobile,
                  'btn-group me-2': !$isMobile,
                }"
                aria-label="Event Actions"
              >
                <RouterLink
                  :to="`/events/${event.id}`"
                  class="btn btn-outline-primary"
                >
                  <font-awesome-icon icon="fa-solid fa-eye" />
                </RouterLink>
                <RouterLink
                  :to="`/events/update/${event.id}`"
                  class="btn btn-outline-primary"
                >
                  <font-awesome-icon icon="fa-solid fa-pen" />
                </RouterLink>
              </div>
              <div class="btn-group me-2" role="group">
                <button
                  type="button"
                  class="btn btn-danger"
                  data-bs-toggle="modal"
                  :data-bs-target="'#deleteEventModal-' + event.id"
                >
                  <font-awesome-icon icon="fa-solid fa-trash" />
                </button>
              </div>
            </div>
          </td>
          <DeleteEventModal
            @event-deleted="handleEventDeleted"
            :event_id="event.id"
          />
        </tr>
      </tbody>
    </table>
    <Paginate
      v-if="page_count > 1"
      :page-count="page_count"
      :click-handler="onPageChange"
    />
  </div>
  <Spinner v-if="status.loading" />
</template>
