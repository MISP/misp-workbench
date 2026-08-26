<script setup>
import { computed, defineAsyncComponent, onMounted, ref } from "vue";
import { Modal } from "bootstrap";
import { storeToRefs } from "pinia";
import { router } from "@/router";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faDiagramProject,
  faList,
  faRotate,
  faSitemap,
} from "@fortawesome/free-solid-svg-icons";
import ApiError from "@/components/misc/ApiError.vue";
import Spinner from "@/components/misc/Spinner.vue";
import { useCorrelationsStore, useToastsStore } from "@/stores";

// The network pulls in the pivotick bundle, so it is only fetched once someone
// actually switches to it.
const CorrelationsNetwork = defineAsyncComponent(
  () => import("@/components/correlations/CorrelationsNetwork.vue"),
);

const correlationsStore = useCorrelationsStore();
const toastsStore = useToastsStore();
const { stats, status } = storeToRefs(correlationsStore);

const rebuildModalEl = ref(null);
const view = ref("list");
let rebuildModal = null;

correlationsStore.getStats();

onMounted(() => {
  rebuildModal = new Modal(rebuildModalEl.value);
});

const totalCorrelations = computed(() => stats.value.total_correlations ?? 0);

/**
 * The aggregation nests the attribute behind a top_hits query. Flatten it here
 * so the template reads as a ranked list instead of a path expression, and keep
 * the share of the busiest entry so each row can show its own magnitude.
 */
function withShare(items) {
  const busiest = Math.max(...items.map((item) => item.count), 0);

  return items.map((item) => ({
    ...item,
    share: busiest ? `${Math.round((item.count / busiest) * 100)}%` : "0%",
  }));
}

const topAttributes = computed(() =>
  withShare(
    (stats.value.top_correlated_attributes || []).map((bucket) => {
      const attribute =
        bucket.top_attribute_info?.hits?.hits?.[0]?._source ?? {};

      return {
        id: bucket.key,
        count: bucket.doc_count,
        type: attribute.target_attribute_type,
        label: attribute.target_attribute_value ?? bucket.key,
        to: `/attributes/${bucket.key}`,
        eventUuid: attribute.target_event_uuid,
      };
    }),
  ),
);

const topEvents = computed(() =>
  withShare(
    (stats.value.top_correlated_events || []).map((bucket) => ({
      id: bucket.key,
      count: bucket.doc_count,
      label: bucket.key,
      to: `/events/${bucket.key}`,
    })),
  ),
);

const rankings = computed(() => [
  {
    key: "attributes",
    title: "Most correlated attributes",
    caption: "Values matched by the largest number of correlations",
    empty: "No attribute has been correlated yet.",
    items: topAttributes.value,
  },
  {
    key: "events",
    title: "Most correlating events",
    caption: "Events whose attributes produce the most correlations",
    empty: "No event has produced a correlation yet.",
    items: topEvents.value,
  },
]);

function navigate(route) {
  router.push(route);
}

function confirmRebuild() {
  rebuildModal?.hide();

  correlationsStore.run().then((response) => {
    // A failed request is reported through status.error by the store.
    if (!response?.task_id) {
      return;
    }

    toastsStore.push(`Rebuilding correlations — task ${response.task_id}`);
    correlationsStore.getStats();
  });
}
</script>

<template>
  <div
    class="d-flex flex-wrap align-items-end justify-content-between gap-3 mb-4"
  >
    <div>
      <h4 class="mb-1">Correlations</h4>
      <p class="page-caption mb-0">
        <template v-if="totalCorrelations">
          {{ totalCorrelations.toLocaleString() }} correlations across the index
        </template>
        <template v-else> Attribute matches found across events </template>
      </p>
    </div>

    <div class="d-flex flex-wrap align-items-center gap-2">
      <div
        class="btn-group btn-group-sm flex-shrink-0"
        role="group"
        aria-label="Correlation view"
      >
        <button
          type="button"
          class="btn"
          :class="view === 'list' ? 'btn-secondary' : 'btn-outline-secondary'"
          :aria-pressed="view === 'list'"
          @click="view = 'list'"
        >
          <FontAwesomeIcon :icon="faList" class="me-1" />Rankings
        </button>
        <button
          type="button"
          class="btn"
          :class="view === 'graph' ? 'btn-secondary' : 'btn-outline-secondary'"
          :aria-pressed="view === 'graph'"
          @click="view = 'graph'"
        >
          <FontAwesomeIcon :icon="faDiagramProject" class="me-1" />Network
        </button>
      </div>

      <button
        class="btn btn-outline-danger btn-sm"
        :disabled="status.generating"
        @click="rebuildModal?.show()"
      >
        <FontAwesomeIcon
          :icon="faRotate"
          class="me-1"
          :spin="status.generating"
        />
        {{ status.generating ? "Rebuilding…" : "Rebuild correlations" }}
      </button>
    </div>
  </div>

  <div v-if="status.error" class="alert alert-danger">
    <ApiError :errors="status.error" />
  </div>

  <Spinner v-if="status.loading" />

  <div v-else-if="!totalCorrelations" class="empty text-center py-5">
    <FontAwesomeIcon :icon="faSitemap" class="empty__icon mb-3" />
    <p class="mb-1">No correlations yet</p>
    <p class="text-body-secondary small mb-0">
      Correlations are created in the background as attributes are added or
      changed. Rebuild them here to correlate everything already indexed.
    </p>
  </div>

  <CorrelationsNetwork v-else-if="view === 'graph'" @navigate="navigate" />

  <div v-else class="d-grid gap-3">
    <section v-for="ranking in rankings" :key="ranking.key" class="card">
      <header class="card-header bg-body-tertiary">
        <h6 class="mb-1">{{ ranking.title }}</h6>
        <p class="page-caption mb-0">{{ ranking.caption }}</p>
      </header>

      <ul v-if="ranking.items.length" class="list-unstyled mb-0 pb-2">
        <li
          v-for="item in ranking.items"
          :key="item.id"
          class="rank-row px-3 pt-2"
        >
          <div class="d-flex align-items-center gap-2">
            <span
              v-if="item.type"
              class="badge bg-info text-dark flex-shrink-0"
            >
              {{ item.type }}
            </span>
            <RouterLink
              :to="item.to"
              class="rank-value text-truncate"
              :title="item.label"
            >
              {{ item.label }}
            </RouterLink>
            <span class="rank-count ms-auto flex-shrink-0">
              {{ item.count.toLocaleString() }}
            </span>
          </div>

          <div v-if="item.eventUuid" class="d-flex align-items-center gap-2">
            <span class="eyebrow flex-shrink-0">Event</span>
            <RouterLink
              :to="`/events/${item.eventUuid}`"
              class="rank-event text-truncate"
              :title="item.eventUuid"
            >
              {{ item.eventUuid }}
            </RouterLink>
          </div>

          <!-- The row rule doubles as the share of the busiest entry. -->
          <div class="rank-bar" aria-hidden="true">
            <span :style="{ width: item.share }"></span>
          </div>
        </li>
      </ul>

      <p v-else class="text-body-secondary small px-3 py-4 mb-0">
        {{ ranking.empty }}
      </p>
    </section>
  </div>

  <div
    ref="rebuildModalEl"
    class="modal fade"
    tabindex="-1"
    aria-labelledby="rebuildCorrelationsLabel"
    aria-hidden="true"
  >
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 id="rebuildCorrelationsLabel" class="modal-title">
            Rebuild all correlations?
          </h5>
          <button
            type="button"
            class="btn-close"
            data-bs-dismiss="modal"
            aria-label="Close"
          ></button>
        </div>
        <div class="modal-body">
          <p>
            Every stored correlation is deleted and built again from the
            attributes currently indexed. The job runs in the background and
            takes a while on large datasets.
          </p>
          <p class="text-body-secondary small mb-0">
            Followers are notified about the correlations found during the
            rebuild, including ones they have already seen.
          </p>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-secondary"
            data-bs-dismiss="modal"
          >
            Cancel
          </button>
          <button type="button" class="btn btn-danger" @click="confirmRebuild">
            Rebuild correlations
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.eyebrow {
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--bs-secondary-color);
}

.page-caption {
  font-size: 0.8125rem;
  color: var(--bs-secondary-color);
}

/* The share bar is the only horizontal rule in a row, so links carry no
   underline until they are hovered. */
.rank-value,
.rank-event {
  font-family: var(--bs-font-monospace);
  min-width: 0;
  text-decoration: none;
}

.rank-value:hover,
.rank-event:hover,
.rank-value:focus-visible,
.rank-event:focus-visible {
  text-decoration: underline;
}

.rank-value {
  flex: 1 1 auto;
  font-size: 0.8125rem;
}

.rank-event {
  font-size: 0.75rem;
  color: var(--bs-secondary-color);
}

.rank-count {
  font-size: 0.8125rem;
  font-variant-numeric: tabular-nums;
  color: var(--bs-body-color);
}

.rank-bar {
  height: 3px;
  margin-top: 0.5rem;
  background-color: var(--bs-border-color-translucent);
}

.rank-bar > span {
  display: block;
  height: 100%;
  background-color: var(--bs-primary);
  opacity: 0.75;
}

.empty__icon {
  font-size: 1.75rem;
  color: var(--bs-secondary-color);
  opacity: 0.6;
}
</style>
