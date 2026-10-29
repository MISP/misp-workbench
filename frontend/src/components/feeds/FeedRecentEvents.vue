<script setup>
import { ref, computed, watch } from "vue";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import { useFeedsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";

dayjs.extend(relativeTime);

const LIMIT = 10;

// The local events the feed's fetches created or updated, most recently
// ingested first (GET /feeds/{id}/events).
const props = defineProps({
  feed: { type: Object, required: true },
});

const feedsStore = useFeedsStore();
const events = ref([]);
const total = ref(0);
const loading = ref(false);
const error = ref(null);

// Every event from this feed, in Explore, however old.
const exploreLink = computed(() => ({
  path: "/explore",
  query: {
    q: `source.type:feed AND source.id:${props.feed.id}`,
    tab: "events",
    range: "all",
  },
}));

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const response = await feedsStore.getRecentEvents(props.feed.id, LIMIT);
    events.value = response.events;
    total.value = response.total;
  } catch (e) {
    error.value = e;
  } finally {
    loading.value = false;
  }
}

function ingestedAgo(event) {
  return event.created_at ? dayjs.unix(event.created_at).fromNow() : null;
}

watch(() => props.feed.id, load, { immediate: true });
</script>

<template>
  <div class="card">
    <div class="card-header d-flex align-items-center">
      <h5 class="mb-0 me-auto">Recent events</h5>
      <RouterLink v-if="total" :to="exploreLink" class="small">
        See all {{ total }} in Explore
      </RouterLink>
    </div>
    <div class="card-body">
      <Spinner v-if="loading" />
      <div v-else-if="error" class="alert alert-danger mb-0">{{ error }}</div>
      <p v-else-if="!events.length" class="text-muted small mb-0">
        No events from this feed yet.
      </p>
      <ul v-else class="list-group list-group-flush">
        <li
          v-for="event in events"
          :key="event.uuid"
          class="list-group-item d-flex align-items-center gap-2 px-0"
        >
          <RouterLink
            :to="`/events/${event.uuid}`"
            class="text-decoration-none text-truncate me-auto"
            :title="event.info"
          >
            {{ event.info }}
          </RouterLink>
          <span class="small text-muted text-nowrap">
            {{ event.attribute_count ?? 0 }} attributes
          </span>
          <span
            class="small text-muted text-nowrap"
            :title="
              ingestedAgo(event)
                ? 'Ingested ' + ingestedAgo(event)
                : 'Ingested before this was recorded'
            "
          >
            {{ ingestedAgo(event) || event.date }}
          </span>
        </li>
      </ul>
    </div>
  </div>
</template>
