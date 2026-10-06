<script setup>
import { computed } from "vue";
import Badge from "@/components/misc/Badge.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import UUID from "@/components/misc/UUID.vue";
import { correlationHelper } from "@/helpers";

const props = defineProps({
  correlation: { type: Object, required: true },
});

const src = computed(() => props.correlation._source);
const sourceType = computed(() =>
  correlationHelper.typeLabel(src.value.source_attribute_type, src.value),
);
const targetType = computed(() =>
  correlationHelper.typeLabel(src.value.target_attribute_type, src.value),
);
</script>

<template>
  <div class="card mb-2 correlation-card">
    <div
      class="card-header py-2 px-3 bg-body-secondary d-flex align-items-center gap-2"
    >
      <Badge :value="src.match_type" />
      <span class="text-muted small">match</span>
      <span
        v-if="src.source_attribute_type"
        class="badge bg-primary-subtle text-primary"
        :title="`${src.source_attribute_type} attribute`"
      >
        {{ sourceType }}
      </span>
    </div>

    <div class="card-body py-2">
      <div class="row g-2">
        <div class="col-md-6">
          <div class="text-muted small mb-1">source</div>
          <div class="small">
            attr:
            <RouterLink
              v-if="src.source_attribute_uuid"
              :to="`/attributes/${src.source_attribute_uuid}`"
              class="text-decoration-none"
            >
              <UUID :uuid="src.source_attribute_uuid" :copy="true" />
            </RouterLink>
          </div>
          <div class="small">
            event:
            <RouterLink
              v-if="src.source_event_uuid"
              :to="`/events/${src.source_event_uuid}`"
              class="text-decoration-none"
            >
              <UUID :uuid="src.source_event_uuid" :copy="true" />
            </RouterLink>
          </div>
        </div>
        <div class="col-md-6">
          <div class="text-muted small mb-1">target</div>
          <div class="fw-semibold text-break">
            <RouterLink
              v-if="src.target_attribute_uuid"
              :to="`/attributes/${src.target_attribute_uuid}`"
              class="text-decoration-none"
            >
              {{ src.target_attribute_value }}
            </RouterLink>
            <span v-else>{{ src.target_attribute_value }}</span>
          </div>
          <div class="small">
            <Badge
              :value="targetType"
              :title="`${src.target_attribute_type} attribute`"
            />
            in
            <RouterLink
              v-if="src.target_event_uuid"
              :to="`/events/${src.target_event_uuid}`"
              class="text-decoration-none"
            >
              <UUID :uuid="src.target_event_uuid" :copy="true" />
            </RouterLink>
          </div>
        </div>
      </div>
    </div>

    <div class="card-footer d-flex justify-content-between text-muted small">
      <Timestamp v-if="src['@timestamp']" :timestamp="src['@timestamp']" />
      <span v-else></span>
      <span v-if="correlation._score != null" class="badge text-bg-secondary">
        score: {{ correlation._score.toFixed(2) }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.correlation-card {
  transition: box-shadow 0.15s ease;
}
.correlation-card:hover {
  box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.08);
}
</style>
