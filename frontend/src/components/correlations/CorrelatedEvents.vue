<script setup>
defineProps({
  results: {
    type: Array,
    required: true,
  },
});
</script>

<template>
  <div class="card">
    <div class="card-header">Related Events</div>
    <div class="card-body p-3">
      <div v-if="results.length">
        <div v-for="event in results" :key="event.key" class="mb-4">
          <div class="d-flex justify-content-between">
            <div>
              <RouterLink :to="`/events/${event.key}`">
                <span class="badge bg-info me-2">{{ event.doc_count }}</span>
                {{ event.key }}
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="text-muted">No correlations found.</div>
    </div>
  </div>
</template>
