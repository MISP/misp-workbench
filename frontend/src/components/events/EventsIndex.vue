<script setup>
import { storeToRefs } from "pinia";
import { useEventsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Paginate from "vuejs-paginate-next";
import EventActions from "@/components/events/EventActions.vue";

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
  width: 100%;
  word-break: break-word;
}

.btn-toolbar {
  flex-wrap: nowrap !important;
}

@media (max-width: 768px) {
  .eventInfoColumn {
    width: auto;
  }

  .btn-toolbar {
    flex-direction: column;
    align-items: flex-end;
  }

  td {
    font-size: 0.9rem;
  }
}
</style>

<template>
  <div v-if="status.error" class="text-danger">
    Error loading events: {{ status.error }}
  </div>
  <div class="table-responsive">
    <table class="table table-striped table-hover">
      <thead>
        <tr>
          <th scope="col">info</th>
          <th scope="col">tags</th>
          <th scope="col">organisation</th>
          <th scope="col">date</th>
          <th scope="col" class="text-end">actions</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="event.uuid" v-for="event in events.items">
          <td class="eventInfoColumn text-start">{{ event.info }}</td>
          <td>
            <TagsIndex :tags="event.tags" />
          </td>
          <td>
            {{ event.organisation.name }}
          </td>
          <td>{{ event.date }}</td>
          <td class="text-end">
            <EventActions
              :event_uuid="event.uuid"
              @event-deleted="handleEventDeleted"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <div class="d-flex justify-content-center mt-3">
      <Paginate
        v-if="page_count > 1"
        :page-count="page_count"
        :click-handler="onPageChange"
      />
    </div>
  </div>
  <Spinner v-if="status.loading" />
</template>
