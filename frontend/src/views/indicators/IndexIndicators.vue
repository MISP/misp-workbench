<script setup>
import { ref, computed } from "vue";
import { storeToRefs } from "pinia";
import { useIndicatorsStore } from "@/stores";
import Spinner from "@/components/misc/Spinner.vue";
import Timestamp from "@/components/misc/Timestamp.vue";
import Pagination from "@/components/misc/Pagination.vue";
import ScoreBadge from "@/components/indicators/ScoreBadge.vue";
import IndicatorDetails from "@/components/indicators/IndicatorDetails.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShield } from "@fortawesome/free-solid-svg-icons";

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
      class="card-header border-bottom d-flex flex-wrap justify-content-between align-items-center gap-1"
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
      <p class="text-muted d-none d-md-block">
        One record per type and value, merged from every event it appears in:
        sources, first and last seen, every tag and the most restrictive TLP,
        and sightings. Exports, feeds, sinks and lookups can send these instead
        of raw attributes.
      </p>

      <form class="row g-2 align-items-center mb-3" @submit.prevent="apply">
        <div class="col-12 col-lg-5">
          <div class="input-group">
            <input
              class="form-control font-monospace"
              v-model="query"
              placeholder='value, or a query like sources.name:"CIRCL"'
              aria-label="Search indicators"
            />
            <button class="btn btn-outline-primary" type="submit">
              Search
            </button>
          </div>
        </div>
        <div class="col-6 col-md-3 col-lg-2">
          <input
            class="form-control"
            v-model="type"
            placeholder="type (ip-dst)"
            aria-label="Type"
          />
        </div>
        <div class="col-6 col-md-3 col-lg-1">
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
        <div class="col-6 col-md-3 col-lg-2">
          <select class="form-select" v-model="sort" aria-label="Sort">
            <option value="score">score</option>
            <option value="last_seen">last seen</option>
            <option value="first_seen">first seen</option>
            <option value="event_count">events</option>
            <option value="updated_at">recently changed</option>
          </select>
        </div>
        <div class="col-6 col-md-3 col-lg-2">
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
                <th class="d-none d-md-table-cell">type</th>
                <th class="d-none d-lg-table-cell text-end">events</th>
                <th class="d-none d-xl-table-cell">sources</th>
                <th class="d-none d-md-table-cell">TLP</th>
                <th class="d-none d-xl-table-cell">first seen</th>
                <th class="d-none d-lg-table-cell">last seen</th>
                <th class="d-none d-lg-table-cell text-end">sightings</th>
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
                  <!-- Takes the room the shown columns leave. -->
                  <td class="indicator-value">
                    <span
                      v-if="indicator.to_ids"
                      class="badge border bg-danger-subtle text-danger border-danger-subtle me-1"
                      title="At least one attribute is flagged for IDS"
                    >
                      <FontAwesomeIcon :icon="faShield" />
                      <span class="visually-hidden">Flagged for IDS</span>
                    </span>
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
                    <span class="font-monospace text-break">{{
                      indicator.value
                    }}</span>
                    <!-- On a phone, what the hidden columns would say. -->
                    <div
                      class="d-md-none small text-body-secondary d-flex flex-wrap align-items-center column-gap-2 mt-1"
                    >
                      <span>{{ indicator.type }}</span>
                      <span
                        >{{ indicator.event_count }}
                        {{
                          indicator.event_count === 1 ? "event" : "events"
                        }}</span
                      >
                      <span
                        v-if="indicator.tlp"
                        class="badge"
                        :class="
                          TLP_CLASSES[indicator.tlp] || 'text-bg-secondary'
                        "
                        >{{ indicator.tlp }}</span
                      >
                      <span
                        v-if="indicator.sightings.positive"
                        class="text-success"
                        title="positive sightings"
                        >+{{ indicator.sightings.positive }}</span
                      >
                      <span
                        v-if="indicator.sightings.false_positive"
                        class="text-danger"
                        title="false-positive sightings"
                        >fp {{ indicator.sightings.false_positive }}</span
                      >
                      <span v-if="indicator.last_seen"
                        >last seen <Timestamp :timestamp="indicator.last_seen"
                      /></span>
                    </div>
                  </td>
                  <td class="d-none d-md-table-cell text-nowrap">
                    {{ indicator.type }}
                  </td>
                  <td class="d-none d-lg-table-cell text-end">
                    {{ indicator.event_count }}
                  </td>
                  <td class="d-none d-xl-table-cell">
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
                  <td class="d-none d-md-table-cell">
                    <span
                      v-if="indicator.tlp"
                      class="badge"
                      :class="TLP_CLASSES[indicator.tlp] || 'text-bg-secondary'"
                      >{{ indicator.tlp }}</span
                    >
                  </td>
                  <td class="d-none d-xl-table-cell small">
                    <Timestamp :timestamp="indicator.first_seen" />
                  </td>
                  <td class="d-none d-lg-table-cell small">
                    <Timestamp :timestamp="indicator.last_seen" />
                  </td>
                  <td class="d-none d-lg-table-cell text-end small">
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
                  <!-- max-width: 0, so long tags are cut to the row, not
                       the row stretched to them. -->
                  <td colspan="9" class="bg-body-tertiary" style="max-width: 0">
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

<style scoped>
/* The usual table trick: a cell sized to what the others leave, so a long
   value wraps inside it rather than widen the table past the screen. */
.indicator-value {
  width: 100%;
  max-width: 0;
}
</style>
