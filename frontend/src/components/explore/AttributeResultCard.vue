<script setup>
import { computed } from "vue";
import Badge from "@/components/misc/Badge.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShield } from "@fortawesome/free-solid-svg-icons";
import UUID from "../misc/UUID.vue";

const props = defineProps({
  attribute: {
    type: Object,
    required: true,
  },
});

const src = computed(() => props.attribute._source);
</script>

<template>
  <div class="card mb-2 attribute-card">
    <div class="card-header d-flex justify-content-between align-items-start">
      <div>
        <div class="fw-bold fs-5 d-flex align-items-center gap-2">
          <span>{{ src.value }}</span>
          <CopyToClipboard :value="src.value" />
        </div>
        <div class="text-muted small">
          <span class="text-success" v-if="src.to_ids">
            <FontAwesomeIcon :icon="faShield" alt="IDS" />
          </span>
          <Badge :value="src.type" class="me-1" />
          <span>{{ src.category }}</span>
        </div>
      </div>

      <div class="text-end small">
        <a :href="`/attributes/${src.uuid}`" class="text-decoration-none">
          <FontAwesomeIcon :icon="faEye" />
        </a>
      </div>
    </div>

    <div class="card-body py-2">
      <div>
        <UUID :uuid="src.uuid" :copy="true" />
      </div>
      <div v-if="src.tags?.length" class="mb-2">
        <TagsIndex :tags="src.tags" />
      </div>

      <div class="d-flex flex-wrap gap-3 small">
        <div v-if="src.event_uuid">
          <strong>Event:</strong>
          <UUID :uuid="src.event_uuid" :copy="true" />
        </div>
      </div>

      <div v-if="src.expanded?.ip2geo" class="mt-2 p-2 rounded small">
        🌍
        {{ src.expanded.ip2geo.country_name }}
        ({{ src.expanded.ip2geo.country_iso_code }}) ·
        {{ src.expanded.ip2geo.continent_name }}
      </div>
    </div>

    <div class="card-footer d-flex justify-content-between text-muted small">
      <div>
        Last edited:
        <Timestamp :timestamp="src.timestamp" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.attribute-card {
  transition: box-shadow 0.15s ease;
}

.attribute-card:hover {
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.08);
}
</style>
