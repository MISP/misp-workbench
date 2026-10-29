<script setup>
import { ref, onMounted } from "vue";
import { fetchWrapper } from "@/helpers";
import Badge from "@/components/misc/Badge.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import IndicatorDetails from "@/components/indicators/IndicatorDetails.vue";
import { useIndicatorsStore } from "@/stores";

// An attribute's fields, the indicator behind its value and its first
// correlations, loaded when its Explore card opens.
const props = defineProps({ attribute: { type: Object, required: true } });

const CORRELATIONS = 5;
const apiUrl = import.meta.env.VITE_API_URL;
const indicatorsStore = useIndicatorsStore();

const indicator = ref(null);
const correlations = ref(null);
const loading = ref(true);

onMounted(async () => {
  const attr = props.attribute;
  const [scores, related] = await Promise.allSettled([
    indicatorsStore.scoresFor([attr]),
    fetchWrapper.get(
      `${apiUrl}/correlations/?` +
        new URLSearchParams({
          source_attribute_uuid: attr.uuid,
          size: CORRELATIONS,
        }),
    ),
  ]);
  const indicatorUuid =
    scores.status === "fulfilled" ? scores.value[attr.uuid]?.uuid : null;
  if (indicatorUuid) {
    try {
      indicator.value = await indicatorsStore.get(indicatorUuid);
    } catch {
      indicator.value = null;
    }
  }
  correlations.value = related.status === "fulfilled" ? related.value : null;
  loading.value = false;
});
</script>

<template>
  <div class="small">
    <dl class="row mb-0 mx-0">
      <dt class="col-sm-2">event</dt>
      <dd class="col-sm-10">
        <RouterLink
          :to="`/events/${attribute.event_uuid}`"
          class="font-monospace"
          >{{ attribute.event_uuid }}</RouterLink
        >
      </dd>
      <template v-if="attribute.object_uuid">
        <dt class="col-sm-2">object</dt>
        <dd class="col-sm-10 font-monospace">{{ attribute.object_uuid }}</dd>
      </template>
      <template v-if="attribute.comment">
        <dt class="col-sm-2">comment</dt>
        <dd class="col-sm-10 text-break">{{ attribute.comment }}</dd>
      </template>
      <dt class="col-sm-2">distribution</dt>
      <dd class="col-sm-10">
        <DistributionLevel :distribution_level_id="attribute.distribution" />
      </dd>
      <template v-if="attribute.first_seen || attribute.last_seen">
        <dt class="col-sm-2">seen</dt>
        <dd class="col-sm-10">
          {{ attribute.first_seen || "?" }} → {{ attribute.last_seen || "?" }}
        </dd>
      </template>
      <dt class="col-sm-2">correlation</dt>
      <dd class="col-sm-10">
        {{ attribute.disable_correlation ? "disabled" : "enabled" }}
      </dd>
      <dt class="col-sm-2">updated</dt>
      <dd class="col-sm-10"><Timestamp :timestamp="attribute.timestamp" /></dd>
    </dl>

    <div v-if="loading" class="text-muted mt-2">Loading…</div>
    <template v-else>
      <h6 class="mt-3">Indicator</h6>
      <IndicatorDetails v-if="indicator" :indicator="indicator" />
      <p v-else class="text-muted mb-0">
        No indicator for this value (context types, such as text, have none).
      </p>

      <h6 class="mt-3">
        Correlations
        <span v-if="correlations" class="text-muted fw-normal"
          >({{ correlations.total }})</span
        >
      </h6>
      <p v-if="!correlations?.results?.length" class="text-muted mb-0">None.</p>
      <ul v-else class="list-unstyled mb-0">
        <li
          v-for="hit in correlations.results"
          :key="hit._id"
          class="d-flex align-items-center gap-2 flex-wrap"
        >
          <Badge :value="hit._source.match_type" />
          <span class="font-monospace text-break">{{
            hit._source.target_attribute_value
          }}</span>
          <RouterLink
            :to="`/events/${hit._source.target_event_uuid}`"
            class="font-monospace"
            >event {{ hit._source.target_event_uuid.slice(0, 8) }}</RouterLink
          >
        </li>
      </ul>
    </template>
  </div>
</template>
