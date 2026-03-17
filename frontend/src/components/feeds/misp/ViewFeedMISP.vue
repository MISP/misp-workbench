<script setup>
const props = defineProps({
  feed: {
    type: Object,
    required: true,
  },
});

function hasRules() {
  return props.feed.rules && Object.keys(props.feed.rules).length > 0;
}

function formatTimestamp(ts) {
  const match = String(ts).match(/^(\d+)([dwm])$/);
  if (!match) return ts;
  const units = { d: "days", w: "weeks", m: "months" };
  return `${match[1]} ${units[match[2]] || match[2]}`;
}
</script>

<template>
  <div class="card">
    <div class="card-header">
      <h5 class="mb-0">MISP Feed Rules</h5>
    </div>
    <div class="card-body">
      <div v-if="!hasRules()" class="text-muted">
        No rules configured. All events will be fetched.
      </div>
      <template v-else>
        <ul class="list-group list-group-flush">
          <li
            v-if="feed.rules.timestamp"
            class="list-group-item d-flex justify-content-between"
          >
            <span>Only fetch events published in the last</span>
            <span class="fw-semibold">{{
              formatTimestamp(feed.rules.timestamp)
            }}</span>
          </li>
          <li
            v-if="feed.rules.tags && feed.rules.tags.length"
            class="list-group-item"
          >
            <div class="mb-1">Only fetch events with tags:</div>
            <span
              v-for="tag in feed.rules.tags"
              :key="tag"
              class="badge bg-secondary me-1"
              >{{ tag }}</span
            >
          </li>
          <li
            v-if="feed.rules.orgs && feed.rules.orgs.length"
            class="list-group-item"
          >
            <div class="mb-1">Only fetch events from organisations:</div>
            <span
              v-for="org in feed.rules.orgs"
              :key="org"
              class="badge bg-secondary me-1"
              >{{ org }}</span
            >
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
