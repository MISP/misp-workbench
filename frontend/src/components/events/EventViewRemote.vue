<script setup>
import { computed } from "vue";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import AttributesIndexRemote from "@/components/attributes/AttributesIndexRemote.vue";
import ReportsIndexRemote from "@/components/reports/ReportsIndexRemote.vue";
import ObjectsIndexRemote from "@/components/objects/ObjectsIndexRemote.vue";
import UUID from "@/components/misc/UUID.vue";
import ThreatLevel from "@/components/enums/ThreatLevel.vue";
import AnalysisLevel from "@/components/enums/AnalysisLevel.vue";
import {
  useRemoteMISPEventsStore,
  useFeedEventsStore,
  useToastsStore,
} from "@/stores";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
  faShapes,
  faTags,
  faCubesStacked,
  faDownload,
} from "@fortawesome/free-solid-svg-icons";

const props = defineProps({
  server_id: { type: [String, Number], default: null },
  feed_id: { type: [String, Number], default: null },
  event_uuid: { type: String, required: true },
});

const isServer = computed(() => !!props.server_id);

const toastsStore = useToastsStore();

// Server store
const remoteMISPEventsStore = useRemoteMISPEventsStore();
const { remote_events, status: serverStatus } = storeToRefs(
  remoteMISPEventsStore,
);

// Feed store
const feedEventsStore = useFeedEventsStore();
const { feed_event, status: feedStatus } = storeToRefs(feedEventsStore);

// Load from the appropriate source
if (isServer.value) {
  remoteMISPEventsStore.get_remote_server_events_index(props.server_id, {
    event_uuid: props.event_uuid,
    limit: 1,
  });
} else {
  feedEventsStore.get_feed_event(props.feed_id, props.event_uuid);
}

// Unified loading/error status
const status = computed(() =>
  isServer.value ? serverStatus.value : feedStatus.value,
);

// Normalised event shape regardless of source
const event = computed(() => {
  if (isServer.value) {
    const e = remote_events.value[0];
    if (!e) return null;
    return {
      id: e.id,
      uuid: e.uuid,
      info: e.info,
      orgc: e.Orgc?.name,
      published: e.published,
      protected: e.protected,
      date: e.date,
      timestamp: e.timestamp,
      threat_level_id: e.threat_level_id,
      analysis: e.analysis,
      distribution: e.distribution,
      attribute_count: e.attribute_count,
      disable_correlation: e.disable_correlation,
      tags: e.EventTag || [],
    };
  } else {
    const e = feed_event.value?.Event;
    if (!e) return null;
    return {
      id: e.id,
      uuid: e.uuid,
      info: e.info,
      orgc: e.Orgc?.name,
      published: e.published,
      protected: e.protected,
      date: e.date,
      timestamp: e.timestamp,
      threat_level_id: e.threat_level_id,
      analysis: e.analysis,
      distribution: e.distribution,
      attribute_count: e.attribute_count,
      disable_correlation: e.disable_correlation,
      tags: e.Tag || [],
      // Feed-only: inline sub-data
      attributes: e.Attribute || [],
      objects: e.Object || [],
      reports: e.EventReport || [],
    };
  }
});

function pullRemoteMISPEvent() {
  toastsStore.push("Event pull enqueued.");
  remoteMISPEventsStore.pull_remote_misp_event(
    props.server_id,
    event.value.uuid,
  );
}

function fetchFeedEvent() {
  toastsStore.push("Feed event fetch enqueued.");
  feedEventsStore.fetch_feed_event(props.feed_id, event.value.uuid);
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
    <!-- Header -->
    <div class="event-title card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ event.info }}</h3>
        </div>
        <div class="col-2 text-end">
          <div class="btn-toolbar float-end" role="toolbar">
            <div class="btn-group" role="group">
              <button
                type="button"
                class="btn btn-outline-primary"
                :title="isServer ? 'Pull Remote Event' : 'Fetch event to local'"
                @click="isServer ? pullRemoteMISPEvent() : fetchFeedEvent()"
              >
                <FontAwesomeIcon :icon="faDownload" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Metadata + reports -->
    <div class="row m-1">
      <div class="col-sm-4 mt-3">
        <div class="card" style="height: 800px">
          <div class="card-body d-flex flex-column">
            <div class="table-responsive-sm">
              <table class="table table-striped">
                <tbody>
                  <tr>
                    <th>uuid</th>
                    <td><UUID :uuid="event.uuid" /></td>
                  </tr>
                  <tr>
                    <th>created by</th>
                    <td>{{ event.orgc }}</td>
                  </tr>
                  <tr>
                    <th>published</th>
                    <td>{{ event.published }}</td>
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
                    <td>{{ event.timestamp }}</td>
                  </tr>
                  <tr>
                    <th>threat level</th>
                    <td>
                      <ThreatLevel
                        :threat_level_id="parseInt(event.threat_level_id)"
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>analysis</th>
                    <td>
                      <AnalysisLevel
                        :analysis_level_id="parseInt(event.analysis)"
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>distribution</th>
                    <td>
                      <DistributionLevel
                        :distribution_level_id="parseInt(event.distribution)"
                      />
                    </td>
                  </tr>
                  <tr>
                    <th>attributes</th>
                    <td>{{ event.attribute_count }}</td>
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
                  <TagsIndex :tags="event.tags" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Reports -->
      <div class="col-sm-8">
        <div class="card-body d-flex flex-column">
          <div class="card-text">
            <ReportsIndexRemote
              v-if="isServer"
              :server_id="server_id"
              :event_id="event.id"
            />
            <ReportsIndexRemote v-else :reports="event.reports" />
          </div>
        </div>
      </div>
    </div>

    <!-- Objects -->
    <div class="row m-1">
      <div class="col-12">
        <div class="card mt-2">
          <div class="card-header">
            <FontAwesomeIcon :icon="faShapes" /> objects
          </div>
          <div class="card-body d-flex flex-column">
            <ObjectsIndexRemote
              v-if="isServer"
              :server_id="server_id"
              :event_uuid="event.uuid"
            />
            <ObjectsIndexRemote v-else :objects="event.objects" />
          </div>
        </div>
      </div>
    </div>

    <!-- Attributes -->
    <div class="row m-1">
      <div class="col-12">
        <div class="card">
          <div class="card-header">
            <FontAwesomeIcon :icon="faCubesStacked" /> attributes
          </div>
          <div class="card-body d-flex flex-column">
            <AttributesIndexRemote
              v-if="isServer && event.attribute_count"
              :server_id="server_id"
              :event_uuid="event.uuid"
            />
            <AttributesIndexRemote
              v-else-if="!isServer"
              :attributes="event.attributes"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
