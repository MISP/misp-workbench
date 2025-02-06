<script setup>
import Spinner from "@/components/misc/Spinner.vue";
import { storeToRefs } from "pinia";
import Sparkline from "@/components/charts/Sparkline.vue";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import UploadAttachmentsWidget from "@/components/events/UploadAttachmentsWidget.vue";
import { router } from "@/router";
import {
  useEventsStore,
  useModulesStore,
  useTaxonomiesStore,
  useGalaxiesStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faPen,
  faDownLong,
  faTags,
  faShapes,
  faCubesStacked,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["event_id"]);

const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);
eventsStore.getById(props.event_id);

const modulesStore = useModulesStore();
modulesStore.get({ enabled: true });

const taxonomiesStore = useTaxonomiesStore();
taxonomiesStore.get({ enabled: true, size: 1000 }); // FIXME: get all taxonomies

const galaxiesStore = useGalaxiesStore();
galaxiesStore.get({ enabled: true, size: 1000 }); // FIXME: get all galaxies

const { taxonomies } = storeToRefs(taxonomiesStore);

function handleEventDeleted() {
  router.push(`/events`);
}

function handleObjectAdded() {
  eventsStore.getById(props.event_id);
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
</style>
<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading event: {{ status.error }}
  </div>
  <div v-if="!status.loading && event" class="card">
    <div class="event-title card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ event.info }}</h3>
        </div>
        <div class="col-2 text-end">
          <div class="btn-toolbar float-end" role="toolbar">
            <div
              class="flex-wrap"
              :class="{
                'btn-group-vertical': $isMobile,
                'btn-group me-2': !$isMobile,
              }"
              aria-label="Event Actions"
            >
              <RouterLink
                :to="`/events/update/${event.id}`"
                class="btn btn-outline-primary"
              >
                <FontAwesomeIcon :icon="faPen" />
              </RouterLink>
            </div>
            <div class="btn-group" role="group">
              <button
                type="button"
                class="btn btn-danger"
                data-bs-toggle="modal"
                :data-bs-target="'#deleteEventModal-' + event.id"
              >
                <FontAwesomeIcon :icon="faTrash" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div class="col-sm-6 mt-2">
        <div class="card">
          <div class="card-body d-flex flex-column">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <tbody>
                  <tr>
                    <th>id</th>
                    <td>{{ event.id }}</td>
                  </tr>
                  <tr>
                    <th>uuid</th>
                    <td>
                      <UUID :uuid="event.uuid" />
                    </td>
                  </tr>
                  <tr>
                    <th>published</th>
                    <td>{{ event.published }}</td>
                  </tr>
                  <tr>
                    <th>creator user</th>
                    <td>{{ event.user_id }}</td>
                  </tr>
                  <tr>
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
                  </tr>
                  <tr>
                    <th>date</th>
                    <td>{{ event.date }}</td>
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
                    <th>disable correlation</th>
                    <td>
                      <div class="form-check form-switch">
                        <input
                          class="form-check-input"
                          type="checkbox"
                          :checked="event.disable_correlation"
                          disabled
                        />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        <div class="mt-2">
          <div class="card h-100">
            <div class="card-header">
              <FontAwesomeIcon :icon="faTags" /> tags
            </div>
            <div class="card-body d-flex flex-column">
              <div class="card-text">
                <TagsSelect
                  v-if="taxonomies.items"
                  :modelClass="'event'"
                  :model="event"
                  :selectedTags="event.tags"
                />
              </div>
            </div>
          </div>
        </div>
        <div class="mt-2">
          <UploadAttachmentsWidget
            :event_id="event.id"
            @object-added="handleObjectAdded"
          />
        </div>
      </div>
      <div class="col col-sm-3">
        <div class="mt-2">
          <div class="card bg-light">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <p class="mb-0 text-muted">activity</p>
                  <Sparkline :data="[2, 3, 5, 7, 18, 8, 6, 15, 23, 20, 21]" />
                </div>
              </div>
            </div>
            <div class="card-footer text-muted">
              <p class="card-text fst-italic fw-light">
                <small class="text-muted"
                  >last day/week/<span class="fw-bold text-decoration-underline"
                    >month</span
                  ></small
                >
              </p>
            </div>
          </div>
        </div>
        <div class="mt-2">
          <div class="card bg-light">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <p class="mb-0 text-muted">correlations</p>
                  <h2>8,523</h2>
                </div>
                <span
                  class="badge badge-pill badge-cyan badge-red bg-warning fs-5"
                >
                  <FontAwesomeIcon :icon="faDownLong" />
                  <span class="font-weight-semibold ml-1">6.71%</span>
                </span>
              </div>
            </div>
            <div class="card-footer text-muted">
              <p class="card-text fst-italic fw-light">
                <small class="text-muted"
                  >last day/<span class="fw-bold text-decoration-underline"
                    >week</span
                  >/month</small
                >
              </p>
            </div>
          </div>
        </div>
        <div class="mt-2">
          <div class="card">
            <div class="card-body bg-light">
              <div class="d-flex justify-content-between align-items-center">
                <div>
                  <p class="mb-0 text-muted">sightings</p>
                  <h2>423</h2>
                </div>
                <span
                  class="badge badge-pill badge-cyan badge-red bg-danger fs-5"
                >
                  <FontAwesomeIcon :icon="faDownLong" />
                  <span class="font-weight-semibold ml-1">16.71%</span>
                </span>
              </div>
            </div>
            <div class="card-footer text-muted">
              <p class="card-text fst-italic fw-light">
                <small class="text-muted"
                  >last day/week/<span class="fw-bold text-decoration-underline"
                    >month</span
                  ></small
                >
              </p>
            </div>
          </div>
        </div>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-12 col-lg-6 col-xl-3">
        <div class="mt-2">
          <div class="card bg-light">
            <div class="card-body d-flex flex-column">
              <div class="card-text">
                <img src="/images/pie-chart.png" class="card-img" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div class="col-12">
        <div class="card">
          <div class="card-header">
            <FontAwesomeIcon :icon="faShapes" /> objects
          </div>
          <div class="card-body d-flex flex-column">
            <ObjectsIndex
              :event_id="event_id"
              :total_size="event.object_count"
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
            <AttributesIndex :event_id="event_id" :page_size="10" />
          </div>
        </div>
      </div>
    </div>
    <div class="card-footer text-muted">
      <p class="card-text">
        <small class="text-muted"
          >last updated 3 mins ago by <a href="/users/123">adulau</a></small
        >
      </p>
    </div>
    <DeleteEventModal
      @event-deleted="handleEventDeleted"
      :event_id="event.id"
    />
  </div>
</template>
