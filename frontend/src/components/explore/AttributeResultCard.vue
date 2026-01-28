<script setup>
import { computed } from "vue";
import Badge from "@/components/misc/Badge.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShield } from "@fortawesome/free-solid-svg-icons";
import AttributeActions from "@/components/attributes/AttributeActions.vue";
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
    <div class="card-header position-relative py-2 px-3 bg-body-secondary">
      <div class="d-flex align-items-center gap-2">
        <span class="fw-semibold">
          <UUID :uuid="src.uuid" :copy="true" />
        </span>
      </div>

      <div class="position-absolute bottom-0 end-0 me-2 mb-1">
        <AttributeActions :attribute="src" />
      </div>
    </div>

    <div class="card-body py-2">
      <div class="flex-grow-1">
        <div class="text-muted small d-flex align-items-center gap-2">
          <Badge :value="src.type" />
          <span class="">{{ src.category }}</span>

          <span
            v-if="src.to_ids"
            class="badge bg-danger-subtle text-danger d-flex align-items-center gap-1"
          >
            <FontAwesomeIcon :icon="faShield" />
            IDS
          </span>
        </div>
        <div v-if="src.type === 'text'" class="mb-1">
          <details>
            <summary class="fw-bold fs-6 d-flex align-items-center gap-2">
              <span
                class="text-truncate"
                style="
                  max-width: 70ch;
                  display: inline-block;
                  white-space: nowrap;
                  overflow: hidden;
                  text-overflow: ellipsis;
                "
              >
                {{
                  src.value && src.value.length > 300
                    ? src.value.slice(0, 200) + "…"
                    : src.value
                }}
              </span>
              <CopyToClipboard :value="src.value" />
            </summary>

            <div class="mt-2">
              <textarea
                class="form-control"
                readonly
                rows="8"
                style="white-space: pre-wrap; overflow: auto"
                v-model="src.value"
              ></textarea>
            </div>
          </details>
        </div>

        <div v-else class="fw-bold fs-6 d-flex align-items-center gap-2">
          <span>{{ src.value }}</span>
          <CopyToClipboard :value="src.value" />
        </div>
      </div>
      <div v-if="src.tags?.length" class="mb-2">
        <TagsIndex :tags="src.tags" />
      </div>

      <div
        v-if="src.expanded?.ip2geo"
        class="geo-box mt-2 p-2 rounded small d-inline-flex align-items-center gap-2"
      >
        🌍
        <span>
          {{ src.expanded.ip2geo.country_name }}
          ({{ src.expanded.ip2geo.country_iso_code }}) ·
          {{ src.expanded.ip2geo.continent_name }}
        </span>
      </div>
    </div>

    <div class="card-footer d-flex justify-content-between text-muted small">
      <span>
        <Timestamp :timestamp="src.timestamp" />
      </span>
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

.geo-box {
  background: var(--bs-light-bg-subtle);
  border-left: 3px solid var(--bs-primary);
}
</style>
