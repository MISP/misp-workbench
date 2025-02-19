<script setup>
import { storeToRefs } from "pinia";
import { useRemoteMISPAttributesStore } from "@/stores";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Pagination from "@/components/misc/Pagination.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";

const props = defineProps(["server_id", "event_uuid", "page_size"]);
const remoteMISPAttributesStore = useRemoteMISPAttributesStore();
const { remote_event_attributes, page, size, status } = storeToRefs(
  remoteMISPAttributesStore,
);

remoteMISPAttributesStore.get_remote_server_event_attributes(
  props.server_id,
  props.event_uuid,
  {
    limit: size.value,
    page: 0,
  },
);

function handleNextPage() {
  page.value = page.value + 1;
  remote_event_attributes.value = [];
  remoteMISPAttributesStore.get_remote_server_event_attributes(
    props.server_id,
    props.event_uuid,
    {
      page: page.value,
      limit: size.value,
    },
  );
}

function handlePrevPage() {
  if (page.value == 0) {
    return;
  }
  remote_event_attributes.value = [];
  page.value = page.value - 1;
  remoteMISPAttributesStore.get_remote_server_event_attributes(
    props.server_id,
    props.event_uuid,
    {
      page: page.value,
      limit: size.value,
    },
  );
}
</script>

<style scoped>
.table {
  table-layout: fixed;
}

.value {
  width: 30%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  box-sizing: border-box;
}
</style>

<template>
  <div class="table-responsive-sm">
    <div v-if="status.error" class="text-danger">
      Error loading attributes: {{ status.error }}
    </div>
    <table class="table table-striped">
      <thead>
        <tr>
          <th scope="col">value</th>
          <th style="width: 400px" scope="col" class="d-none d-sm-table-cell">
            tags
          </th>
          <th scope="col">type</th>
          <th scope="col" class="d-none d-sm-table-cell">timestamp</th>
          <th scope="col" class="d-none d-sm-table-cell">distribution</th>
        </tr>
      </thead>
      <tbody>
        <tr :key="attribute.id" v-for="attribute in remote_event_attributes">
          <td class="value">
            <CopyToClipboard :value="attribute.value" />
            {{ attribute.value }}
          </td>
          <td class="d-none d-sm-table-cell">
            <TagsIndex :tags="attribute.Tag || []" />
          </td>
          <td>{{ attribute.type }}</td>
          <td class="d-none d-sm-table-cell">
            <Timestamp :timestamp="attribute.timestamp" />
          </td>
          <td class="d-none d-sm-table-cell">
            <DistributionLevel
              :distribution_level_id="parseInt(attribute.distribution)"
            />
          </td>
        </tr>
      </tbody>
    </table>
    <Spinner v-if="status.loading" />
    <div class="mt-3">
      <Pagination
        @nextPageClick="handleNextPage()"
        @prevPageClick="handlePrevPage()"
        :currentPage="page"
        :hasPrevPage="page > 0"
        :hasNextPage="remote_event_attributes.length >= size"
      />
    </div>
  </div>
</template>
