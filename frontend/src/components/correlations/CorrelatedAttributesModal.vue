<script setup>
import { computed, ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faCopy,
  faMagnifyingGlass,
  faSitemap,
  faXmark,
} from "@fortawesome/free-solid-svg-icons";

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
const APPROXIMATE_MATCH_TYPES = ["fuzzy", "prefix"];

const query = ref("");
const expandedEvents = ref(new Set());

const modalId = computed(
  () => props.id || `correlatedAttributesModal${props.attribute.uuid}`,
);

const correlations = computed(() => props.attribute.correlations || []);

function matchesQuery(source, needle) {
  return [
    source.target_attribute_value,
    source.target_attribute_type,
    source.target_event_uuid,
    source.match_type,
  ].some((field) =>
    String(field ?? "")
      .toLowerCase()
      .includes(needle),
  );
}

function bestScore(attribute) {
  return Math.max(...attribute.matches.map((match) => match.score ?? 0));
}

/**
 * Correlations arrive as one document per matched pair, so the same attribute
 * shows up once per match type. Group them by event and merge them per
 * attribute: the question this panel answers is "which other events hold this
 * indicator", and the match types belong to the row, not to a row of their own.
 */
function groupCorrelations(needle) {
  const groups = new Map();

  for (const correlation of correlations.value) {
    const source = correlation._source;

    if (needle && !matchesQuery(source, needle)) {
      continue;
    }

    let group = groups.get(source.target_event_uuid);
    if (!group) {
      group = { eventUuid: source.target_event_uuid, attributes: new Map() };
      groups.set(group.eventUuid, group);
    }

    let attribute = group.attributes.get(source.target_attribute_uuid);
    if (!attribute) {
      attribute = {
        uuid: source.target_attribute_uuid,
        type: source.target_attribute_type,
        value: source.target_attribute_value,
        matches: [],
        seenAt: null,
      };
      group.attributes.set(attribute.uuid, attribute);
    }

    attribute.matches.push({
      type: source.match_type,
      score: source.score,
    });

    const seenAt = source["@timestamp"];
    if (seenAt && (!attribute.seenAt || seenAt > attribute.seenAt)) {
      attribute.seenAt = seenAt;
    }
  }

  return [...groups.values()]
    .map((group) => ({
      eventUuid: group.eventUuid,
      attributes: [...group.attributes.values()].sort(
        (a, b) => bestScore(b) - bestScore(a) || a.value.localeCompare(b.value),
      ),
    }))
    .sort(
      (a, b) =>
        b.attributes.length - a.attributes.length ||
        a.eventUuid.localeCompare(b.eventUuid),
    );
}

const allGroups = computed(() => groupCorrelations(""));
const eventGroups = computed(() =>
  groupCorrelations(query.value.trim().toLowerCase()),
);

const totalAttributes = computed(() =>
  allGroups.value.reduce((total, group) => total + group.attributes.length, 0),
);
const shownAttributes = computed(() =>
  eventGroups.value.reduce(
    (total, group) => total + group.attributes.length,
    0,
  ),
);

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
  return APPROXIMATE_MATCH_TYPES.includes(matchType);
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
          </div>

          <div v-if="eventGroups.length" class="d-grid gap-3">
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

          <div v-else-if="filtering" class="empty text-center py-5">
            <p class="mb-2">Nothing matches “{{ query }}”.</p>
            <button
              type="button"
              class="btn btn-sm btn-outline-secondary"
              @click="query = ''"
            >
              Clear filter
            </button>
          </div>

          <div v-else class="empty text-center py-5">
            <FontAwesomeIcon :icon="faSitemap" class="empty__icon mb-3" />
            <p class="mb-1">No correlations yet</p>
            <p class="text-body-secondary small mb-0">
              This attribute has no matching values in other events.
              Correlations are created in the background when an attribute is
              added or its value changes.
            </p>
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
