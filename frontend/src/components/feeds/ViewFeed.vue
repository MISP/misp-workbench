<script setup>
import DeleteFeedModal from "@/components/feeds/DeleteFeedModal.vue";
import { Modal } from "bootstrap";
import { ref, onMounted } from "vue";
import { router } from "@/router";

const props = defineProps(["feed"]);

const deleteFeedModal = ref(null);

onMounted(() => {
  deleteFeedModal.value = new Modal(
    document.getElementById(`deleteFeedModal_${props.feed.id}`),
  );
});

function handleFeedDeleted(event) {
  router.push(`/feeds`);
}

function openDeleteFeedModal() {
  deleteFeedModal.value.show();
}
</script>

<template>
  <div class="card">
    <div class="card-header border-bottom">
      <div class="row">
        <div class="col-10">
          <h3>{{ feed.name }}</h3>
        </div>
        <div class="col-2 text-end">
          <div class="btn-toolbar float-end" role="toolbar">
            <div
              :class="{
                'btn-group-vertical': $isMobile,
                'btn-group me-2': !$isMobile,
              }"
              role="group"
              aria-label="Feed Actions"
            >
              <RouterLink
                :to="`/feeds/update/${feed.id}`"
                class="btn btn-outline-primary"
              >
                <font-awesome-icon icon="fa-solid fa-pen" />
              </RouterLink>
            </div>
            <div class="btn-group me-2" role="group">
              <button
                type="button"
                class="btn btn-danger"
                @click="openDeleteFeedModal"
              >
                <font-awesome-icon icon="fa-solid fa-trash" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="card-body d-flex flex-column">
      <div class="table-responsive-sm">
        <table class="table table-striped">
          <tbody>
            <tr>
              <th style="width: 30%">id</th>
              <td>{{ feed.id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">provider</th>
              <td>{{ feed.provider }}</td>
            </tr>
            <tr>
              <th style="width: 30%">url</th>
              <td>{{ feed.url }}</td>
            </tr>
            <tr>
              <th style="width: 30%">rules</th>
              <td>{{ feed.rules }}</td>
            </tr>
            <tr>
              <th style="width: 30%">enabled</th>
              <td>{{ feed.enabled }}</td>
            </tr>
            <tr>
              <th style="width: 30%">distribution</th>
              <td>{{ feed.distribution }}</td>
            </tr>
            <tr>
              <th style="width: 30%">sharing_group_id</th>
              <td>{{ feed.sharing_group_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">tag_id</th>
              <td>{{ feed.tag_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">default</th>
              <td>{{ feed.default }}</td>
            </tr>
            <tr>
              <th style="width: 30%">source_format</th>
              <td>{{ feed.source_format }}</td>
            </tr>
            <tr>
              <th style="width: 30%">fixed_event</th>
              <td>{{ feed.fixed_event }}</td>
            </tr>
            <tr>
              <th style="width: 30%">delta_merge</th>
              <td>{{ feed.delta_merge }}</td>
            </tr>
            <tr>
              <th style="width: 30%">event_id</th>
              <td>{{ feed.event_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">publish</th>
              <td>{{ feed.publish }}</td>
            </tr>
            <tr>
              <th style="width: 30%">override_ids</th>
              <td>{{ feed.override_ids }}</td>
            </tr>
            <tr>
              <th style="width: 30%">settings</th>
              <td>{{ feed.settings }}</td>
            </tr>
            <tr>
              <th style="width: 30%">input_source</th>
              <td>{{ feed.input_source }}</td>
            </tr>
            <tr>
              <th style="width: 30%">delete_local_file</th>
              <td>{{ feed.delete_local_file }}</td>
            </tr>
            <tr>
              <th style="width: 30%">lookup_visible</th>
              <td>{{ feed.lookup_visible }}</td>
            </tr>
            <tr>
              <th style="width: 30%">headers</th>
              <td>{{ feed.headers }}</td>
            </tr>
            <tr>
              <th style="width: 30%">caching_enabled</th>
              <td>{{ feed.caching_enabled }}</td>
            </tr>
            <tr>
              <th style="width: 30%">force_to_ids</th>
              <td>{{ feed.force_to_ids }}</td>
            </tr>
            <tr>
              <th style="width: 30%">orgc_id</th>
              <td>{{ feed.orgc_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">tag_collection_id</th>
              <td>{{ feed.tag_collection_id }}</td>
            </tr>
            <tr>
              <th style="width: 30%">cached_elements</th>
              <td>{{ feed.cached_elements }}</td>
            </tr>
            <tr>
              <th style="width: 30%">coverage_by_other_feeds</th>
              <td>{{ feed.coverage_by_other_feeds }}</td>
            </tr>
          </tbody>
        </table>
        <DeleteFeedModal
          @feed-deleted="handleFeedDeleted"
          :feed_id="feed.id"
          :modal="deleteFeedModal"
        />
      </div>
    </div>
  </div>
</template>
