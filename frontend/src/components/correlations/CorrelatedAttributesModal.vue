<script setup>
import { computed, defineAsyncComponent, ref } from "vue";
import { router } from "@/router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faCopy,
  faDiagramProject,
  faList,
  faMagnifyingGlass,
  faSitemap,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";
import { correlationHelper } from "@/helpers";

// The graph pulls in the pivotick bundle, so it is only fetched once someone
// actually switches to it.
const CorrelationGraph = defineAsyncComponent(
  () => import("@/components/correlations/CorrelationGraph.vue"),
);

const props = defineProps({
  attribute: {
    type: Object,
    required: true,
  },
  modal: {
    type: Object,
    default: null,
  },
  id: {
    type: String,
    default: null,
  },
});

// Attributes shown per event before the group has to be expanded, so an
// attribute correlating with a thousand others still renders instantly.
const COLLAPSED_GROUP_SIZE = 25;

const query = ref("");
const view = ref("list");
const expandedEvents = ref(new Set());

const modalId = computed(
  () => props.id || `correlatedAttributesModal${props.attribute.uuid}`,
);

const correlations = computed(() => props.attribute.correlations || []);

/**
 * The filter drives both views, so it is applied to the raw documents and the
 * merging happens after. See `correlationHelper` for why one attribute can
 * arrive as several documents.
 */
const filteredCorrelations = computed(() => {
  const needle = query.value.trim().toLowerCase();

  return correlations.value.filter((correlation) =>
    correlationHelper.matchesQuery(correlation._source, needle),
  );
});

const allAttributes = computed(() =>
  correlationHelper.mergeCorrelatedAttributes(correlations.value),
);
const filteredAttributes = computed(() =>
  correlationHelper.mergeCorrelatedAttributes(filteredCorrelations.value),
);

const allGroups = computed(() =>
  correlationHelper.groupByEvent(allAttributes.value),
);
const eventGroups = computed(() =>
  correlationHelper.groupByEvent(filteredAttributes.value),
);

const totalAttributes = computed(() => allAttributes.value.length);
const shownAttributes = computed(() => filteredAttributes.value.length);

const lastCorrelatedAt = computed(() =>
  correlations.value.reduce((latest, correlation) => {
    const seenAt = correlation._source["@timestamp"];

    return seenAt && (!latest || seenAt > latest) ? seenAt : latest;
  }, null),
);

const filtering = computed(() => query.value.trim() !== "");
const filterable = computed(() => totalAttributes.value > 6);

function visibleAttributes(group) {
  if (expandedEvents.value.has(group.eventUuid) || filtering.value) {
    return group.attributes;
  }

  return group.attributes.slice(0, COLLAPSED_GROUP_SIZE);
}

function hiddenCount(group) {
  return group.attributes.length - visibleAttributes(group).length;
}

function expandEvent(eventUuid) {
  expandedEvents.value = new Set(expandedEvents.value).add(eventUuid);
}

function isApproximate(matchType) {
  return correlationHelper.isApproximateMatch(matchType);
}

function formatSeenAt(timestamp) {
  if (!timestamp) {
    return "";
  }

  const date = new Date(timestamp);

  return Number.isNaN(date.getTime())
    ? timestamp
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
}

function copyValue(value) {
  navigator.clipboard.writeText(value);
}

function hideModal() {
  props.modal?.hide();
}

function navigate(route) {
  hideModal();
  router.push(route);
}
</script>

<template>
  <div
    :id="modalId"
    class="modal fade"
    tabindex="-1"
    :aria-labelledby="`${modalId}Label`"
    aria-hidden="true"
  >
    <div
      class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable"
    >
      <div class="modal-content">
        <div class="modal-header align-items-start">
          <div class="me-3 min-w-0">
            <h5 :id="`${modalId}Label`" class="modal-title mb-1">
              Correlations
            </h5>
            <div class="d-flex align-items-center gap-2 min-w-0">
              <span class="badge bg-info text-dark flex-shrink-0">{{
                attribute.type
              }}</span>
              <span
                class="subject-value text-truncate"
                :title="attribute.value"
              >
                {{ attribute.value }}
              </span>
            </div>
          </div>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>

        <div class="modal-body">
          <div
            v-if="totalAttributes"
            class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3"
          >
            <p class="eyebrow mb-0">
              <template v-if="filtering">
                {{ shownAttributes }} of {{ totalAttributes }} attributes
              </template>
              <template v-else>
                {{ totalAttributes }}
                {{ totalAttributes === 1 ? "attribute" : "attributes" }} in
                {{ allGroups.length }}
                {{ allGroups.length === 1 ? "event" : "events" }}
                <template v-if="lastCorrelatedAt">
                  &middot; last correlated {{ formatSeenAt(lastCorrelatedAt) }}
                </template>
              </template>
            </p>

            <div class="d-flex flex-wrap align-items-center gap-2">
              <div v-if="filterable" class="filter input-group input-group-sm">
                <span class="input-group-text">
                  <FontAwesomeIcon :icon="faMagnifyingGlass" />
                </span>
                <input
                  v-model="query"
                  type="search"
                  class="form-control"
                  aria-label="Filter correlations"
                  placeholder="Filter by value, type or event"
                />
                <button
                  v-if="filtering"
                  type="button"
                  class="btn btn-outline-secondary"
                  title="Clear filter"
                  @click="query = ''"
                >
                  <FontAwesomeIcon :icon="faXmark" />
                </button>
              </div>

              <div
                class="btn-group btn-group-sm flex-shrink-0"
                role="group"
                aria-label="Correlation view"
              >
                <button
                  type="button"
                  class="btn"
                  :class="
                    view === 'list' ? 'btn-secondary' : 'btn-outline-secondary'
                  "
                  :aria-pressed="view === 'list'"
                  @click="view = 'list'"
                >
                  <FontAwesomeIcon :icon="faList" class="me-1" />List
                </button>
                <button
                  type="button"
                  class="btn"
                  :class="
                    view === 'graph' ? 'btn-secondary' : 'btn-outline-secondary'
                  "
                  :aria-pressed="view === 'graph'"
                  @click="view = 'graph'"
                >
                  <FontAwesomeIcon :icon="faDiagramProject" class="me-1" />Graph
                </button>
              </div>
            </div>
          </div>

          <div v-if="!totalAttributes" class="empty text-center py-5">
            <FontAwesomeIcon :icon="faSitemap" class="empty__icon mb-3" />
            <p class="mb-1">No correlations yet</p>
            <p class="text-body-secondary small mb-0">
              This attribute has no matching values in other events.
              Correlations are created in the background when an attribute is
              added or its value changes.
            </p>
          </div>

          <div v-else-if="!shownAttributes" class="empty text-center py-5">
            <p class="mb-2">Nothing matches “{{ query }}”.</p>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="query = ''"
            >
              Clear filter
            </button>
          </div>

          <CorrelationGraph
            v-else-if="view === 'graph'"
            :attribute="attribute"
            :correlations="filteredCorrelations"
            @navigate="navigate"
          />

          <div v-else class="d-grid gap-3">
            <section
              v-for="group in eventGroups"
              :key="group.eventUuid"
              class="event-group"
            >
              <header
                class="event-group__header d-flex flex-wrap align-items-center gap-2 px-3 py-2"
              >
                <span class="eyebrow flex-shrink-0">Event</span>
                <RouterLink
                  :to="`/events/${group.eventUuid}`"
                  class="event-uuid text-truncate"
                  :title="group.eventUuid"
                  @click="hideModal"
                >
                  {{ group.eventUuid }}
                </RouterLink>
                <span class="eyebrow ms-auto flex-shrink-0">
                  {{ group.attributes.length }}
                  {{
                    group.attributes.length === 1 ? "attribute" : "attributes"
                  }}
                </span>
              </header>

              <div
                v-for="correlated in visibleAttributes(group)"
                :key="correlated.uuid"
                class="correlation-row d-flex align-items-center gap-2 px-3 py-2"
              >
                <span class="badge bg-info text-dark flex-shrink-0">{{
                  correlated.type
                }}</span>

                <RouterLink
                  :to="`/attributes/${correlated.uuid}`"
                  class="correlation-value text-truncate"
                  :title="correlated.value"
                  @click="hideModal"
                >
                  {{ correlated.value }}
                </RouterLink>

                <span class="row-meta d-flex align-items-center gap-2 ms-auto">
                  <span
                    v-for="match in correlated.matches"
                    :key="`${correlated.uuid}-${match.type}`"
                    class="match-chip"
                    :class="{
                      'match-chip--approximate': isApproximate(match.type),
                    }"
                    :title="`Match score ${match.score}`"
                  >
                    {{ match.type }}
                  </span>

                  <button
                    type="button"
                    class="copy-value btn btn-sm p-0 border-0"
                    title="Copy value to clipboard"
                    aria-label="Copy value to clipboard"
                    @click="copyValue(correlated.value)"
                  >
                    <FontAwesomeIcon :icon="faCopy" />
                  </button>
                </span>
              </div>

              <button
                v-if="hiddenCount(group)"
                type="button"
                class="btn btn-sm btn-link w-100 py-2"
                @click="expandEvent(group.eventUuid)"
              >
                Show {{ hiddenCount(group) }} more from this event
              </button>
            </section>
          </div>
        </div>

        <div class="modal-footer">
          <button
            id="closeModalButton"
            type="button"
            data-bs-dismiss="modal"
            class="btn btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.min-w-0 {
  min-width: 0;
}

.eyebrow {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bs-secondary-color);
}

.subject-value {
  font-family: var(--bs-font-monospace);
  font-size: 0.9375rem;
}

.filter {
  width: min(20rem, 100%);
}

.event-group {
  border: 1px solid var(--bs-border-color);
  border-left: 3px solid var(--bs-primary);
  border-radius: var(--bs-border-radius);
  overflow: hidden;
}

.event-group__header {
  background-color: var(--bs-tertiary-bg);
  border-bottom: 1px solid var(--bs-border-color);
}

.event-uuid,
.correlation-value {
  font-family: var(--bs-font-monospace);
  font-size: 0.8125rem;
  min-width: 0;
}

.correlation-value {
  flex: 1 1 auto;
}

.correlation-row + .correlation-row {
  border-top: 1px solid var(--bs-border-color-translucent);
}

.row-meta {
  flex-shrink: 0;
}

@media (max-width: 575.98px) {
  .correlation-row {
    flex-wrap: wrap;
  }
}

.correlation-row:hover {
  background-color: var(--bs-tertiary-bg);
}

/* The value is the link worth clicking, so copying stays quiet until hovered. */
.copy-value {
  color: var(--bs-secondary-color);
}

.copy-value:hover,
.copy-value:focus-visible {
  color: var(--bs-link-hover-color);
}

.match-chip {
  border: 1px solid var(--bs-border-color);
  border-radius: 999px;
  padding: 0.0625rem 0.5rem;
  font-size: 0.6875rem;
  letter-spacing: 0.02em;
  color: var(--bs-secondary-color);
  white-space: nowrap;
}

/* An inexact match needs reading before it is trusted, so it is flagged. */
.match-chip--approximate {
  border-color: var(--bs-warning-border-subtle);
  color: var(--bs-warning-text-emphasis);
}

.empty__icon {
  font-size: 1.75rem;
  color: var(--bs-secondary-color);
  opacity: 0.6;
}
</style>
