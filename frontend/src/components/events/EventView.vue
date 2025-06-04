<script setup>
import Spinner from "@/components/misc/Spinner.vue";
import { storeToRefs } from "pinia";
import AttributesIndex from "@/components/attributes/AttributesIndex.vue";
import ObjectsIndex from "@/components/objects/ObjectsIndex.vue";
import TagsSelect from "@/components/tags/TagsSelect.vue";
import ReportsIndex from "@/components/reports/ReportsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import DeleteEventModal from "@/components/events/DeleteEventModal.vue";
import UploadAttachmentsWidget from "@/components/attachments/UploadAttachmentsWidget.vue";
import { router } from "@/router";
import { useEventsStore, useModulesStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faTrash,
  faPen,
  faTags,
  faShapes,
  faCubesStacked,
} from "@fortawesome/free-solid-svg-icons";
import Timestamp from "@/components/misc/Timestamp.vue";

const props = defineProps(["event_id"]);

const eventsStore = useEventsStore();
const { event, status } = storeToRefs(eventsStore);
eventsStore.getById(props.event_id);

const modulesStore = useModulesStore();
modulesStore.get({ enabled: true });

function handleEventDeleted() {
  router.push(`/events`);
}

function handleObjectAdded() {
  event.value.object_count += 1;
}

function handleObjectDeleted() {
  event.value.object_count -= 1;
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
      <div class="col-sm-4 mt-2">
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
                    <th>timestamp</th>
                    <td><Timestamp :timestamp="event.timestamp" /></td>
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
      <div class="col col-sm-8 mt-2">
        <ReportsIndex :event_id="event.id" />
      </div>
    </div>
    <div class="row">
      <div class="row m-1">
        <div class="col-12">
          <UploadAttachmentsWidget
            :event_id="event.id"
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
                :event_id="event_id"
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
    </div>
    <DeleteEventModal
      @event-deleted="handleEventDeleted"
      :event_id="event.id"
    />
  </div>
</template>
