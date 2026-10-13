<script setup>
import { ref, watch } from "vue";
import { useIndicatorsStore } from "@/stores";
import QualityRate from "@/components/indicators/QualityRate.vue";

// How this feed's, server's or organisation's indicators hold up.
const props = defineProps({
  kind: { type: String, required: true },
  sourceId: { type: [Number, String], default: null },
});

const indicatorsStore = useIndicatorsStore();
const quality = ref(null);
const loaded = ref(false);

watch(
  () => [props.kind, props.sourceId],
  async () => {
    loaded.value = false;
    quality.value =
      props.sourceId === null || props.sourceId === undefined
        ? null
        : await indicatorsStore.sourceQualityFor(props.kind, props.sourceId);
    loaded.value = true;
  },
  { immediate: true },
);
</script>

<template>
  <div class="card mt-3">
    <div class="card-header d-flex justify-content-between align-items-center">
      <span>Indicator quality</span>
      <RouterLink to="/indicators/sources" class="small"
        >all sources</RouterLink
      >
    </div>
    <div class="card-body small">
      <span v-if="!loaded" class="text-muted">Loading…</span>
      <span v-else-if="!quality" class="text-muted"
        >No indicators from this source yet.</span
      >
      <dl v-else class="row mb-0">
        <dt class="col-sm-4">indicators</dt>
        <dd class="col-sm-8">
          {{ quality.indicators.toLocaleString() }}
          <span class="text-muted"
            >({{ quality.exclusive.toLocaleString() }} reported by no one
            else)</span
          >
        </dd>
        <dt class="col-sm-4">also reported by</dt>
        <dd class="col-sm-8">
          <span v-if="!quality.top_overlaps.length" class="text-muted"
            >nobody else</span
          >
          <span
            v-for="other in quality.top_overlaps"
            :key="other.key"
            class="me-2"
            >{{ other.name }} ({{ other.indicators }})</span
          >
        </dd>
        <dt class="col-sm-4">sighted</dt>
        <dd class="col-sm-8">
          <QualityRate :value="quality.hit_rate" /> in the scoring window
        </dd>
        <dt class="col-sm-4">reported benign</dt>
        <dd class="col-sm-8">
          <QualityRate :value="quality.false_positive_rate" good="low" /> in the
          scoring window
          <span v-if="quality.adaptive_penalty" class="text-muted"
            >· adaptive trust: −{{ quality.adaptive_penalty }}</span
          >
        </dd>
        <dt class="col-sm-4">average score</dt>
        <dd class="col-sm-8">
          {{ quality.average_score ?? "—" }}
          <span class="text-muted"
            >(<QualityRate :value="quality.decayed_rate" good="none" />
            decayed)</span
          >
        </dd>
      </dl>
    </div>
  </div>
</template>
