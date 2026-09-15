<script setup>
import { storeToRefs } from "pinia";
import {
  ref,
  onMounted,
  computed,
  reactive,
  watch,
  defineAsyncComponent,
} from "vue";
import Spinner from "@/components/misc/Spinner.vue";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import CreateOrEditReportModal from "@/components/reports/CreateOrEditReportModal.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import ReportsIndex from "@/components/reports/ReportsIndex.vue";
import AnalystDataIndex from "@/components/analyst-data/AnalystDataIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import EventActions from "@/components/events/EventActions.vue";
import UploadAttachmentsWidget from "@/components/attachments/UploadAttachmentsWidget.vue";
import CorrelatedEvents from "@/components/correlations/CorrelatedEvents.vue";
import RelatedVulnerabilities from "@/components/vulnerabilities/RelatedVulnerabilities.vue";
import RetentionBadge from "@/components/events/RetentionBadge.vue";
import { router } from "@/router";
import { Modal } from "bootstrap";
import {
  useEventsStore,
  useModulesStore,
  useCorrelationsStore,
  useReportsStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTags,
  faShapes,
  faCubesStacked,
  faPlus,
  faCommentDots,
  faFileLines,
  faCircleInfo,
  faDiagramProject,
} from "@fortawesome/free-solid-svg-icons";
import Timestamp from "@/components/misc/Timestamp.vue";
import { THREAT_LEVEL } from "@/helpers/constants";

const props = defineProps({
  event_uuid: {
    type: String,
    required: true,
  },
  /** Which tab the URL asked for. See TABS; anything else falls back. */
  tab: {
    type: String,
    default: "overview",
  },
});

const reports_last_updated = ref(parseInt(Date.now() / 1000));

const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);
const reportsStore = useReportsStore();
const correlationsStore = useCorrelationsStore();
const { correlated_events } = storeToRefs(correlationsStore);

const retentionConfig = ref(null);
eventsStore.retentionStatus().then((config) => {
  retentionConfig.value = config;
});

eventsStore.getById(props.event_uuid);
correlationsStore.getTopCorrelatingEvents(props.event_uuid);

const modulesStore = useModulesStore();
modulesStore.get({ enabled: true });

const createOrEditReportModal = ref(null);
onMounted(() => {
  createOrEditReportModal.value = new Modal(
    document.getElementById(`createOrEditReportModal_${props.event_uuid}`),
  );
});

/**
 * Loaded on demand: the graph pulls in pivotick and the MISP icon set, which
 * together are larger than the rest of the app. Paired with the `v-if` on its
 * panel, nothing is fetched until someone opens the tab.
 */
const EventGraph = defineAsyncComponent(
  () => import("@/components/events/EventGraph.vue"),
);

const TABS = [
  { id: "overview", label: "Overview", icon: faCircleInfo },
  { id: "attributes", label: "Attributes", icon: faCubesStacked },
  { id: "objects", label: "Objects", icon: faShapes },
  { id: "graph", label: "Graph", icon: faDiagramProject },
  { id: "analyst-data", label: "Analyst Data", icon: faCommentDots },
];

const activeTab = computed(() =>
  TABS.some((tab) => tab.id === props.tab) ? props.tab : "overview",
);

/**
 * Which panels have been opened at least once.
 *
 * A panel is mounted the first time its tab is selected and then kept alive
 * behind `v-show` - so the graph does not build a force simulation nobody
 * asked for, and a table does not refetch every time you glance at another
 * tab and come back.
 */
const visited = reactive(new Set());

// Driven by the route rather than by the click, so a deep link, a refresh and
// the back button all mount the panel they land on.
watch(activeTab, (id) => visited.add(id), { immediate: true });

function selectTab(id) {
  // The tab lives in the URL so it can be linked, refreshed and stepped back
  // through - a graph worth showing someone is a graph worth having a link to.
  router.push(
    id === "overview"
      ? `/events/${props.event_uuid}`
      : `/events/${props.event_uuid}/${id}`,
  );
}

function tabCount(id) {
  if (id === "attributes") {
    return event.value.attribute_count;
  }

  if (id === "objects") {
    return event.value.object_count;
  }

  return null;
}

/**
 * Threat level as a badge for the page header. The enum components render the
 * raw SCREAMING_SNAKE name, which is fine in a table cell and shouting in a
 * title block - and only a stated level is worth a badge at all.
 */
const THREAT_LEVELS = {
  [THREAT_LEVEL.HIGH]: { label: "high", variant: "text-bg-danger" },
  [THREAT_LEVEL.MEDIUM]: { label: "medium", variant: "text-bg-warning" },
  [THREAT_LEVEL.LOW]: { label: "low", variant: "text-bg-info" },
};

const threatLevel = computed(() => THREAT_LEVELS[event.value.threat_level]);

/** "9 attributes in 3 objects", without the empty halves. */
const eventScale = computed(() => {
  const attributes = event.value.attribute_count ?? 0;
  const objects = event.value.object_count ?? 0;
  const attributeLabel = `${attributes} attribute${attributes === 1 ? "" : "s"}`;

  if (!objects) {
    return attributeLabel;
  }

  return `${attributeLabel} in ${objects} object${objects === 1 ? "" : "s"}`;
});

const eventCorrelationEnabled = computed(() => {
  return !event.value.disable_correlation;
});

// show/hide additional event metadata (id, creator, date)
const showMore = ref(false);
function toggleShowMore() {
  showMore.value = !showMore.value;
}

function openCreateorEditReportModal() {
  createOrEditReportModal.value.show();
}

function handleEventDeleted() {
  router.push(`/events`);
}

function handleObjectCreated() {
  event.value.object_count += 1;
}

function handleObjectDeleted() {
  event.value.object_count -= 1;
}

function togglePublished() {
  if (event.value.published) {
    eventsStore.publish(event.value.uuid).catch(() => {
      event.value.published = !event.value.published;
    });
  } else {
    eventsStore.unpublish(event.value.uuid).catch(() => {
      event.value.published = !event.value.published;
    });
  }
}

function toggleDisableCorrelation() {
  event.value.disable_correlation = !event.value.disable_correlation;
  eventsStore.toggleCorrelation(event.value.uuid).catch(() => {
    // revert the switch
    event.value.disable_correlation = !event.value.disable_correlation;
  });
}

function handleReportCreated() {
  reportsStore.getReportsByEventId(props.event_uuid);
}
function handleReportUpdated() {
  reportsStore.getReportsByEventId(props.event_uuid);
}
function handleReportDeleted() {
  reportsStore.getReportsByEventId(props.event_uuid);
}
</script>

<style scoped>
.single-stat-card .card-body {
  font-size: x-large;
  text-align: center;
  padding: 0;
}

div.row h3 {
  margin-bottom: 0;
}

.single-stat-card .card-body p {
  margin-bottom: 0;
}

.table-fixed {
  table-layout: fixed;
  width: 100%;
}

/* The panel carries the border the tabs sit on, so it must paint the same
   background the active tab does - otherwise the tab's notch shows a seam. */
.tab-panels {
  background-color: var(--bs-body-bg);
}

/* A long event name has to be able to shrink inside the flex row rather than
   pushing the actions off the edge. */
.min-width-0 {
  min-width: 0;
}
</style>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading event: {{ status.error }}
  </div>
  <div v-if="!status.loading && event">
    <!-- The event's name is the page title, on the page rather than inside a
         card header - the same shape as the hunt and feed detail views. What
         used to be an unlabelled toggle buried in the metadata table (is it
         published? how far does it travel?) is stated here instead, because it
         is true on every tab. The uuid is an identifier, not a title, and
         stays in the Overview table where it can be copied. -->
    <div class="d-flex justify-content-between align-items-start gap-3 mb-3">
      <div class="min-width-0">
        <h4 class="mb-1 text-break">{{ event.info }}</h4>
        <div class="d-flex flex-wrap align-items-center gap-2 small">
          <span
            class="badge"
            :class="event.published ? 'text-bg-success' : 'text-bg-secondary'"
          >
            {{ event.published ? "published" : "not published" }}
          </span>
          <span v-if="threatLevel" class="badge" :class="threatLevel.variant">
            {{ threatLevel.label }} threat
          </span>
          <span class="text-body-secondary">{{ eventScale }}</span>
          <span class="text-body-secondary">
            updated <Timestamp :timestamp="event.timestamp" />
          </span>
          <RetentionBadge
            v-if="retentionConfig && event.timestamp"
            :event-timestamp="event.timestamp"
            :retention-config="retentionConfig"
            :tags="event.tags || []"
          />
        </div>
      </div>
      <div class="flex-shrink-0">
        <EventActions
          :event_uuid="event.uuid"
          @event-deleted="handleEventDeleted"
        />
      </div>
    </div>

    <ul class="nav nav-tabs">
      <li v-for="tabItem in TABS" :key="tabItem.id" class="nav-item">
        <button
          type="button"
          class="nav-link"
          :class="{ active: activeTab === tabItem.id }"
          :aria-current="activeTab === tabItem.id ? 'page' : undefined"
          @click="selectTab(tabItem.id)"
        >
          <FontAwesomeIcon :icon="tabItem.icon" /> {{ tabItem.label }}
          <span
            v-if="tabCount(tabItem.id) != null"
            class="badge ms-1"
            :class="
              activeTab === tabItem.id ? 'text-bg-primary' : 'text-bg-secondary'
            "
          >
            {{ tabCount(tabItem.id) }}
          </span>
        </button>
      </li>
    </ul>

    <div class="tab-panels border border-top-0 rounded-bottom p-3">
      <!-- Overview -->
      <div
        v-if="visited.has('overview')"
        v-show="activeTab === 'overview'"
        class="row"
        data-tab-panel="overview"
      >
        <div class="col-sm-4">
          <div class="table-responsive-sm">
            <table class="table table-striped table-fixed">
              <tbody>
                <tr>
                  <th style="width: 150px">uuid</th>
                  <td class="overflow-hidden">
                    <UUID :uuid="event.uuid" />
                  </td>
                </tr>
                <tr>
                  <th>distribution</th>
                  <td>
                    <DistributionLevel
                      :distribution_level_id="event.distribution"
                    />
                  </td>
                </tr>
                <tr>
                  <th>correlate</th>
                  <td>
                    <div class="form-check form-switch">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        id="eventDisableCorrelationSwitch"
                        v-model="eventCorrelationEnabled"
                        @change="toggleDisableCorrelation"
                      />
                    </div>
                  </td>
                </tr>
                <tr>
                  <th>published</th>
                  <td>
                    <div class="form-check form-switch">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        id="eventPublishedSwitch"
                        v-model="event.published"
                        @change="togglePublished"
                      />
                    </div>
                  </td>
                </tr>
                <template v-if="showMore">
                  <tr>
                    <th>creator user</th>
                    <td>{{ event.user_id }}</td>
                  </tr>
                  <tr>
                    <th>threat level</th>
                    <td>
                      <ThreatLevel :threat_level_id="event.threat_level" />
                    </td>
                  </tr>
                  <tr>
                    <th>analysis</th>
                    <td>
                      <AnalysisLevel :analysis_level_id="event.analysis" />
                    </td>
                  </tr>
                  <tr>
                    <th>created at</th>
                    <td>{{ event.date }}</td>
                  </tr>
                </template>

                <!-- toggle row -->
                <tr>
                  <td colspan="2" class="text-end">
                    <button
                      type="button"
                      class="btn btn-sm btn-link"
                      @click="toggleShowMore"
                      :aria-expanded="showMore"
                    >
                      {{ showMore ? "Show less" : "Show more" }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="col col-sm-4">
          <div class="card mb-2">
            <div class="card-header">
              <FontAwesomeIcon :icon="faTags" /> tags
            </div>
            <div class="card-body">
              <TagsSelect
                :modelClass="'event'"
                :model="event"
                :selectedTags="event.tags"
              />
            </div>
          </div>
          <RelatedVulnerabilities :event_uuid="event.uuid" />
        </div>
        <div class="col col-sm-4">
          <CorrelatedEvents :results="correlated_events" />
        </div>
        <div class="col-12 mt-2">
          <div class="card">
            <div class="card-header">
              <FontAwesomeIcon :icon="faFileLines" /> Reports
            </div>
            <div class="card-body d-flex flex-column">
              <ReportsIndex
                :event_uuid="event.uuid"
                :key="reports_last_updated"
                @report-updated="handleReportUpdated"
                @report-deleted="handleReportDeleted"
              />
              <div class="mt-4 text-center">
                <button
                  type="button"
                  class="btn btn-outline-primary"
                  data-placement="top"
                  data-toggle="tooltip"
                  title="Create Event Report"
                  @click="openCreateorEditReportModal"
                >
                  <FontAwesomeIcon :icon="faPlus" /> Create Event Report
                </button>
              </div>
            </div>
          </div>
        </div>
        <div class="col-12 mt-2 event-attachments">
          <UploadAttachmentsWidget
            :event_uuid="event.uuid"
            :key="event.object_count"
            @object-created="handleObjectCreated"
            @object-deleted="handleObjectDeleted"
          />
        </div>
      </div>

      <!-- Attributes -->
      <div
        v-if="visited.has('attributes')"
        v-show="activeTab === 'attributes'"
        data-tab-panel="attributes"
      >
        <AttributesIndex
          :event_uuid="event.uuid"
          :page_size="10"
          @object-created="handleObjectCreated"
        />
      </div>

      <!-- Objects -->
      <div
        v-if="visited.has('objects')"
        v-show="activeTab === 'objects'"
        data-tab-panel="objects"
      >
        <ObjectsIndex
          :event_uuid="event.uuid"
          :page_size="10"
          :key="event.object_count"
        />
      </div>

      <!-- Graph -->
      <div
        v-if="visited.has('graph')"
        v-show="activeTab === 'graph'"
        data-tab-panel="graph"
      >
        <EventGraph :event_uuid="event.uuid" />
      </div>

      <!-- Analyst Data -->
      <div
        v-if="visited.has('analyst-data')"
        v-show="activeTab === 'analyst-data'"
        data-tab-panel="analyst-data"
      >
        <AnalystDataIndex :object_uuid="event.uuid" :object_type="'Event'" />
      </div>
    </div>
  </div>
  <CreateOrEditReportModal
    :key="event_uuid"
    :id="`createOrEditReportModal_${event_uuid}`"
    @report-created="handleReportCreated"
    :modal="createOrEditReportModal"
    :event_uuid="event_uuid"
  />
</template>
