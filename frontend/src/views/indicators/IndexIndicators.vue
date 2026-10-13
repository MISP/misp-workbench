<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useIndicatorsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";
import IndicatorDetails from "@/components/indicators/IndicatorDetails.vue";

const indicatorsStore = useIndicatorsStore();
const { page, indicatorsStatus, status } = storeToRefs(indicatorsStore);

const query = ref("");
const type = ref("");
const idsOnly = ref(true);
const sort = ref("last_seen");
const minScore = ref(null);
const currentPage = ref(1);
const expanded = ref(null);
const SIZE = 50;

const REVIEW_CLASSES = {
  approved: "text-bg-success",
  rejected: "text-bg-dark",
  snoozed: "text-bg-light border",
};

const TLP_CLASSES = {
  "tlp:red": "text-bg-danger",
  "tlp:amber+strict": "text-bg-warning",
  "tlp:amber": "text-bg-warning",
  "tlp:green": "text-bg-success",
  "tlp:clear": "text-bg-light border",
  "tlp:white": "text-bg-light border",
};

function load() {
  expanded.value = null;
  indicatorsStore.search({
    q: query.value.trim(),
    type: type.value.trim(),
    to_ids: idsOnly.value ? true : null,
    sort: sort.value,
    min_score: minScore.value || null,
    page: currentPage.value,
    size: SIZE,
  });
}

function apply() {
  currentPage.value = 1;
  load();
}

function goTo(delta) {
  currentPage.value += delta;
  load();
}

const hasNextPage = computed(
  () => currentPage.value * SIZE < (page.value.total || 0),
);

function sourceLabel(source) {
  return source.type === "feed" || source.type === "server"
    ? `${source.type}: ${source.name}`
    : source.name || source.type;
}

function toggle(indicator) {
  expanded.value = expanded.value === indicator.uuid ? null : indicator.uuid;
}

indicatorsStore.getStatus();
load();
</script>

<template>
  <div class="card">
    <div
      class="card-header border-bottom d-flex justify-content-between align-items-center"
    >
      <h4 class="mb-0">Indicators</h4>
      <small v-if="indicatorsStatus" class="text-muted">
        <template v-if="indicatorsStatus.built">
          {{ indicatorsStatus.indicators.toLocaleString() }} indicators · synced
          <Timestamp :timestamp="indicatorsStatus.synced_at" />
        </template>
        <template v-else
          >Not built yet; the first build is on its way.</template
        >
      </small>
    </div>
    <div class="card-body">
      <p class="text-muted">
        One record per type and value, merged from every event it appears in:
        sources, first and last seen, every tag and the most restrictive TLP,
        and sightings. Exports, feeds, sinks and lookups can send these instead
        of raw attributes.
      </p>

      <form class="row g-2 align-items-center mb-3" @submit.prevent="apply">
        <div class="col-12 col-md-4">
          <input
            class="form-control font-monospace"
            v-model="query"
            placeholder='value, or a query like sources.name:"CIRCL"'
            aria-label="Search indicators"
          />
        </div>
        <div class="col-6 col-md-2">
          <input
            class="form-control"
            v-model="type"
            placeholder="type (ip-dst)"
            aria-label="Type"
          />
        </div>
        <div class="col-6 col-md-1">
          <input
            class="form-control"
            type="number"
            min="0"
            max="100"
            v-model.number="minScore"
            placeholder="min score"
            aria-label="Minimum score"
            title="Only indicators scoring at least this (0-100)"
          />
        </div>
        <div class="col-6 col-md-2">
          <select class="form-select" v-model="sort" aria-label="Sort">
            <option value="score">score</option>
            <option value="last_seen">last seen</option>
            <option value="first_seen">first seen</option>
            <option value="event_count">events</option>
            <option value="updated_at">recently changed</option>
          </select>
        </div>
        <div class="col-6 col-md-2">
          <div class="form-check form-switch mb-0">
            <input
              id="indicators-ids-only"
              class="form-check-input"
              type="checkbox"
              v-model="idsOnly"
              @change="apply"
            />
            <label class="form-check-label" for="indicators-ids-only"
              >IDS only</label
            >
          </div>
        </div>
        <div class="col-6 col-md-1 text-end">
          <button class="btn btn-outline-primary w-100" type="submit">
            Search
          </button>
        </div>
      </form>

      <Spinner v-if="status.loading" />
      <div v-else-if="status.error" class="alert alert-danger">
        {{ status.error }}
      </div>
      <template v-else>
        <div class="text-muted small mb-2">
          {{ page.total.toLocaleString() }} matching
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle">
            <thead>
              <tr>
                <th>score</th>
                <th>value</th>
                <th>type</th>
                <th class="text-end">events</th>
                <th>sources</th>
                <th>TLP</th>
                <th>first seen</th>
                <th>last seen</th>
                <th class="text-end">sightings</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="indicator in page.items" :key="indicator.uuid">
                <tr
                  role="button"
                  :class="{ 'table-active': expanded === indicator.uuid }"
                  @click="toggle(indicator)"
                >
                  <td>
                    <ScoreBadge
                      :score="indicator.score"
                      :breakdown="indicator.score_breakdown"
                    />
                  </td>
                  <td class="font-monospace text-break">
                    <span
                      v-if="indicator.to_ids"
                      class="badge text-bg-primary me-1"
                      title="At least one attribute is flagged for IDS"
                      >IDS</span
                    >
                    <span
                      v-for="issue in indicator.validation_issues || []"
                      :key="issue"
                      class="badge text-bg-danger me-1"
                      :title="`Validation issue on one of its attributes: ${issue}`"
                      >{{ issue }}</span
                    >
                    <span
                      v-if="indicator.review"
                      class="badge me-1"
                      :class="REVIEW_CLASSES[indicator.review.status]"
                      :title="`Review: ${indicator.review.status}`"
                      >{{ indicator.review.status }}</span
                    >
                    <span
                      v-if="indicator.warninglist_hits.length"
                      class="badge text-bg-warning me-1"
                      :title="indicator.warninglist_hits.join(', ')"
                      >warninglist</span
                    >
                    {{ indicator.value }}
                  </td>
                  <td>{{ indicator.type }}</td>
                  <td class="text-end">{{ indicator.event_count }}</td>
                  <td>
                    <span
                      v-for="source in indicator.sources.slice(0, 3)"
                      :key="`${source.type}-${source.id}-${source.name}`"
                      class="badge text-bg-secondary me-1"
                      >{{ sourceLabel(source) }}</span
                    >
                    <span
                      v-if="indicator.sources.length > 3"
                      class="text-muted small"
                      >+{{ indicator.sources.length - 3 }}</span
                    >
                  </td>
                  <td>
                    <span
                      v-if="indicator.tlp"
                      class="badge"
                      :class="TLP_CLASSES[indicator.tlp] || 'text-bg-secondary'"
                      >{{ indicator.tlp }}</span
                    >
                  </td>
                  <td class="small">
                    <Timestamp :timestamp="indicator.first_seen" />
                  </td>
                  <td class="small">
                    <Timestamp :timestamp="indicator.last_seen" />
                  </td>
                  <td class="text-end small">
                    <span
                      v-if="indicator.sightings.positive"
                      class="text-success"
                      title="positive sightings"
                      >+{{ indicator.sightings.positive }}</span
                    >
                    <span
                      v-if="indicator.sightings.false_positive"
                      class="text-danger ms-1"
                      title="false-positive sightings"
                      >fp {{ indicator.sightings.false_positive }}</span
                    >
                  </td>
                </tr>
                <tr v-if="expanded === indicator.uuid">
                  <td colspan="9" class="bg-body-tertiary">
                    <IndicatorDetails :indicator="indicator" />
                  </td>
                </tr>
              </template>
              <tr v-if="!page.items.length">
                <td colspan="9" class="text-center text-muted py-4">
                  No indicators match.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Pagination
          :currentPage="currentPage"
          :hasPrevPage="currentPage > 1"
          :hasNextPage="hasNextPage"
          @prevPageClick="goTo(-1)"
          @nextPageClick="goTo(1)"
        />
      </template>
    </div>
  </div>
</template>
