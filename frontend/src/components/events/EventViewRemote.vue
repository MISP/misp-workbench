<script setup>
import Spinner from "@/components/misc/Spinner.vue";
import { storeToRefs } from "pinia";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import AttributesIndexRemote from "@/components/attributes/AttributesIndexRemote.vue";
import ReportsIndexRemote from "@/components/reports/ReportsIndexRemote.vue";
import ObjectsIndexRemote from "@/components/objects/ObjectsIndexRemote.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import { useRemoteMISPEventsStore, useToastsStore } from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faShapes,
  faTags,
  faCubesStacked,
  faDownload,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps(["server_id", "event_uuid"]);

const toastsStore = useToastsStore();

const remoteMISPEventsStore = useRemoteMISPEventsStore();
const { remote_events, status } = storeToRefs(remoteMISPEventsStore);

remoteMISPEventsStore.get_remote_server_events_index(props.server_id, {
  event_uuid: props.event_uuid,
  limit: 1,
});

function pullRemoteMISPEvent(event_uuid) {
  // toastsStore.push("Event pull enqueued. Task ID: " + response.task.id);
  toastsStore.push("Event pull enqueued.");
  remoteMISPEventsStore.pull_remote_misp_event(props.server_id, event_uuid);
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
  <div v-if="!status.loading && remote_events[0]" class="card">
    <div class="event-title card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ remote_events[0].info }}</h3>
        </div>
        <div class="col-2 text-end">
          <div class="btn-toolbar float-end" role="toolbar">
            <div class="btn-group" role="group">
              <button
                type="button"
                class="btn btn-outline-primary"
                title="Pull Remote Event"
                @click="pullRemoteMISPEvent(remote_events[0].uuid)"
              >
                <FontAwesomeIcon :icon="faDownload" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div class="col-sm-4 mt-2">
        <div class="card" style="height: 800px">
          <div class="card-body d-flex flex-column">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <tbody>
                  <tr>
                    <th>id</th>
                    <td>{{ remote_events[0].id }}</td>
                  </tr>
                  <tr>
                    <th>uuid</th>
                    <td>
                      <UUID :uuid="remote_events[0].uuid" />
                    </td>
                  </tr>
                  <tr>
                    <th>created by</th>
                    <td>
                      {{ remote_events[0].Orgc.name }}
                    </td>
                  </tr>
                  <tr>
                    <th>published</th>
                    <td>{{ remote_events[0].published }}</td>
                  </tr>
                  <tr>
                    <th>protected</th>
                    <td>
                      <div class="form-check form-switch">
                        <input
                          class="form-check-input"
                          type="checkbox"
                          :checked="remote_events[0].protected"
                          disabled
                        />
                      </div>
                    </td>
                  </tr>
                  <tr>
                    <th>date</th>
                    <td>{{ remote_events[0].date }}</td>
                  </tr>
                  <tr>
                    <th>threat level</th>
                    <td>
                      <ThreatLevel
                        :threat_level_id="
                          parseInt(remote_events[0].threat_level_id)
                        "
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>analysis</th>
                    <td>
                      <AnalysisLevel
                        :analysis_level_id="parseInt(remote_events[0].analysis)"
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>distribution</th>
                    <td>
                      <DistributionLevel
                        :distribution_level_id="
                          parseInt(remote_events[0].distribution)
                        "
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>attributes</th>
                    <td>
                      {{ remote_events[0].attribute_count }}
                    </td>
                  </tr>
                  <tr>
                    <th>disable correlation</th>
                    <td>
                      <div class="form-check form-switch">
                        <input
                          class="form-check-input"
                          type="checkbox"
                          :checked="remote_events[0].disable_correlation"
                          disabled
                        />
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="card mt-3" style="height: 280px">
              <div class="card-header">
                <FontAwesomeIcon :icon="faTags" /> tags
              </div>
              <div class="card-body d-flex flex-column">
                <div class="card-text">
                  <TagsIndex :tags="remote_events[0].EventTag" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="col-sm-8">
        <div class="card-body d-flex flex-column">
          <div class="card-text">
            <ReportsIndexRemote
              :server_id="server_id"
              :event_id="remote_events[0].id"
            />
          </div>
        </div>
      </div>
    </div>
    <div class="row m-1">
      <div class="col-12">
        <div class="card mt-2">
          <div class="card-header">
            <FontAwesomeIcon :icon="faShapes" /> objects
          </div>
          <div class="card-body d-flex flex-column">
            <ObjectsIndexRemote
              :server_id="server_id"
              :event_uuid="remote_events[0].uuid"
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
            <AttributesIndexRemote
              v-if="remote_events[0].attribute_count"
              :server_id="server_id"
              :event_uuid="remote_events[0].uuid"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
