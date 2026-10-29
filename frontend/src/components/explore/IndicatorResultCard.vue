<script setup>
import { computed } from "vue";
import Badge from "@/components/misc/Badge.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShield } from "@fortawesome/free-solid-svg-icons";
import IndicatorDetails from "@/components/indicators/IndicatorDetails.vue";
import ExpandToggle from "./ExpandToggle.vue";
import { useCardExpand } from "./useCardExpand";

const props = defineProps({
  indicator: { type: Object, required: true },
});

const src = computed(() => props.indicator._source);
const { expanded, onCardClick } = useCardExpand();

function sourceLabel(source) {
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.name || source.type;
}
</script>

<template>
  <div
    class="card mb-2 indicator-card result-card"
    :class="{ 'border-primary': expanded }"
    @click="onCardClick"
  >
    <div class="card-body py-2">
      <div class="text-muted small d-flex align-items-center gap-2 flex-wrap">
        <ScoreBadge :score="src.score" :breakdown="src.score_breakdown" />
        <Badge :value="src.type" />
        <span
          v-if="src.to_ids"
          class="badge bg-danger-subtle text-danger d-flex align-items-center gap-1"
        >
          <FontAwesomeIcon :icon="faShield" />
          IDS
        </span>
        <span v-if="src.tlp" class="badge text-bg-light border">{{
          src.tlp
        }}</span>
        <span
          v-for="issue in src.validation_issues || []"
          :key="issue"
          class="badge bg-danger-subtle text-danger-emphasis"
          >{{ issue }}</span
        >
        <span
          v-if="src.warninglist_hits?.length"
          class="badge bg-warning-subtle text-warning-emphasis"
          :title="src.warninglist_hits.join(', ')"
          >warninglist</span
        >
      </div>
      <div class="fw-bold fs-6 font-monospace text-break my-1">
        <CopyToClipboard :value="src.value" /> {{ src.value }}
      </div>
      <div class="small text-muted d-flex flex-wrap gap-3">
        <span
          >{{ src.event_count }} event{{
            src.event_count === 1 ? "" : "s"
          }}</span
        >
        <span v-if="src.sources?.length">
          {{ src.sources.map(sourceLabel).join(", ") }}
        </span>
        <span v-if="src.last_seen"
          >last seen <Timestamp :timestamp="src.last_seen"
        /></span>
        <span v-if="src.sightings?.positive"
          >+{{ src.sightings.positive }} sightings</span
        >
        <RouterLink
          v-for="eventUuid in (src.events || []).slice(0, 3)"
          :key="eventUuid"
          :to="`/events/${eventUuid}`"
          class="font-monospace"
          >{{ eventUuid.slice(0, 8) }}</RouterLink
        >
        <ExpandToggle
          class="ms-auto"
          :expanded="expanded"
          @toggle="expanded = !expanded"
        />
      </div>
    </div>
    <div v-if="expanded" class="card-body border-top">
      <IndicatorDetails :indicator="src" />
    </div>
  </div>
</template>

<style scoped>
.result-card {
  cursor: pointer;
}
</style>
