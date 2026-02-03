<script setup>
import { storeToRefs } from "pinia";
import { ref, onMounted, computed } from "vue";
import Spinner from "@/components/misc/Spinner.vue";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import CreateOrEditReportModal from "@/components/reports/CreateOrEditReportModal.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import ReportsIndex from "@/components/reports/ReportsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import EventActions from "@/components/events/EventActions.vue";
import UploadAttachmentsWidget from "@/components/attachments/UploadAttachmentsWidget.vue";
import CorrelatedEvents from "@/components/correlations/CorrelatedEvents.vue";
import RelatedVulnerabilities from "@/components/vulnerabilities/RelatedVulnerabilities.vue";
import { router } from "@/router";
import { Modal } from "bootstrap";
import {
  useEventsStore,
  useModulesStore,
  useCorrelationsStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTags,
  faShapes,
  faCubesStacked,
  faPlus,
} from "@fortawesome/free-solid-svg-icons";
import Timestamp from "@/components/misc/Timestamp.vue";

const props = defineProps(["event_uuid"]);

const reports_last_updated = ref(parseInt(Date.now() / 1000));

const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);
const correlationsStore = useCorrelationsStore();
const { correlated_events } = storeToRefs(correlationsStore);

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

function handleObjectAdded() {
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
  setTimeout(() => {
    reports_last_updated.value = parseInt(Date.now() / 1000);
  }, 100);
}
function handleReportUpdated() {
  setTimeout(() => {
    reports_last_updated.value = parseInt(Date.now() / 1000);
  }, 100);
}
function handleReportDeleted() {
  setTimeout(() => {
    reports_last_updated.value = parseInt(Date.now() / 1000);
  }, 100);
}
</script>

<style>
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

.table.table-striped {
  margin-bottom: 0;
}

.table-fixed {
  table-layout: fixed;
  width: 100%;
}
</style>
<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading event: {{ status.error }}
  </div>
  <div v-if="!status.loading && event" class="card">
    <div class="event-title card-header border-bottom">
      <div class="row align-items-center">
        <div class="col-md-8 col-sm-12">
          <h6 class="mb-0 text-truncate">Event #{{ event.uuid }}</h6>
        </div>
        <div
          class="col-md-4 col-sm-12 text-md-end text-sm-start mt-sm-2 mt-md-0"
        >
          <EventActions
            :event_uuid="event.uuid"
            @event-deleted="handleEventDeleted"
          />
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div>
        <div class="alert alert-info h5 mt-2" role="alert">
          {{ event.info }}
        </div>
      </div>
      <div class="col-sm-4">
        <div class="card">
          <div class="card-body d-flex flex-column">
            <div class="table-responsive-sm">
              <table class="table table-striped table-fixed">
                <tbody>
                  <tr>
                    <th style="width: 150px">uuid</th>
                    <td class="overflow-hidden">
                      <UUID :uuid="event.uuid" />
                    </td>
                  </tr>
                  <!-- TODO handle protected events -->
                  <!-- <tr>
                    <th>protected</th>
                    <td>
                      <div class="form-check form-switch">
                        <input
                          class="form-check-input"
                          type="checkbox"
                          :checked="event.protected"
                          disabled
                        />
                      </div>
                    </td>
                  </tr> -->
                  <tr>
                    <th>distribution</th>
                    <td>
                      <DistributionLevel
                        :distribution_level_id="event.distribution"
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>attributes</th>
                    <td>
                      {{ event.attribute_count }} ({{ event.object_count }}
                      objects)
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
                  <tr>
                    <th>last change at</th>
                    <td>
                      <Timestamp :timestamp="event.timestamp" />
                    </td>
                  </tr>
                  <template v-if="showMore">
                    <tr>
                      <th>local id</th>
                      <td>{{ event.id }}</td>
                    </tr>
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
                        aria-expanded="{{ showMore }}"
                      >
                        {{ showMore ? "Show less" : "Show more" }}
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="card mt-3">
              <div class="card-header">
                <FontAwesomeIcon :icon="faTags" /> tags
              </div>
              <div class="card-body d-flex flex-column">
                <div class="card-text">
                  <TagsSelect
                    :modelClass="'event'"
                    :model="event"
                    :selectedTags="event.tags"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="col col-sm-4 mt-2">
        <RelatedVulnerabilities :event_uuid="event.uuid" />
      </div>
      <div class="col col-sm-4 mt-2">
        <CorrelatedEvents :results="correlated_events" />
      </div>
      <div class="col col-sm-12">
        <div class="card mt-2">
          <div class="card-header">
            <div class="row">
              <div class="col-10">Reports</div>
            </div>
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
    </div>
    <div class="row">
      <div class="row m-1">
        <div class="col-12">
          <UploadAttachmentsWidget
            :event_uuid="event.uuid"
            :key="event.object_count"
            @object-added="handleObjectAdded"
            @object-deleted="handleObjectDeleted"
          />
          <div class="card mt-2">
            <div class="card-header">
              <FontAwesomeIcon :icon="faShapes" /> objects
            </div>
            <div class="card-body d-flex flex-column">
              <ObjectsIndex
                :event_uuid="event.uuid"
                :page_size="10"
                :key="event.object_count"
              />
            </div>
          </div>
        </div>
      </div>
      <div class="row m-1">
        <div class="col-12">
          <div class="card">
            <div class="card-header">
              <FontAwesomeIcon :icon="faCubesStacked" /> attributes
            </div>
            <div class="card-body d-flex flex-column">
              <AttributesIndex :event_uuid="event.uuid" :page_size="10" />
            </div>
          </div>
        </div>
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
