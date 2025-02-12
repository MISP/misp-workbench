<script setup>
import { useServersStore } from "@/stores";
import { storeToRefs } from "pinia";
import Spinner from "@/components/misc/Spinner.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faDownload, faEye } from "@fortawesome/free-solid-svg-icons";

const serversStore = useServersStore();

const props = defineProps(["server"]);
const { remote_events, status } = storeToRefs(serversStore);

serversStore.get_remote_server_events_index(props.server.id);

function pullRemoteMISPEvent(event_uuid) {
  serversStore.pull_remote_misp_event(props.server.id, event_uuid);
}
</script>

<template>
  <div>
    <div class="table-responsive-sm">
      <table class="table table-striped">
        <thead>
          <tr>
            <th scope="col">id</th>
            <th scope="col">info</th>
            <th scope="col">timestamp</th>
            <th scope="col">organisation</th>
            <th scope="col" class="d-none d-sm-table-cell">tags</th>
            <th scope="col" width="20%" class="text-end">actions</th>
          </tr>
        </thead>
        <tbody>
          <Spinner v-if="status.loading" />
          <tr v-for="event in remote_events">
            <td>{{ event.uuid }}</td>
            <td>{{ event.info }}</td>
            <td>{{ event.timestamp }}</td>
            <td>{{ event.Org.name }}</td>
            <td>
              <TagsIndex :tags="event.EventTag" />
            </td>
            <td>
              <div class="text-end">
                <div
                  class="flex-wrap btn-group"
                  aria-label="Remote Event Actions"
                >
                  <RouterLink
                    :to="`/servers/explore/${server.id}/events/${event.uuid}`"
                    class="btn btn-outline-primary"
                  >
                    <FontAwesomeIcon :icon="faEye" />
                  </RouterLink>
                  <button
                    type="button"
                    class="btn btn-outline-primary"
                    data-placement="top"
                    title="Pull Remote Event"
                    @click="pullRemoteMISPEvent(event.uuid)"
                  >
                    <FontAwesomeIcon :icon="faDownload" />
                  </button>
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
