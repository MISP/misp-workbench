<script setup>
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRemoteMISPAttributesStore } from "@/stores";
import DistributionLevel from "@/components/enums/DistributionLevel.vue";
import TagsIndex from "@/components/tags/TagsIndex.vue";
import Spinner from "@/components/misc/Spinner.vue";
import Pagination from "@/components/misc/Pagination.vue";
import CopyToClipboard from "@/components/misc/CopyToClipboard.vue";
import Timestamp from "@/components/misc/Timestamp.vue";

const props = defineProps({
  // Server mode: fetch from API
  server_id: { type: [String, Number], default: null },
  event_uuid: { type: String, default: null },
  page_size: { type: Number, default: null },
  // Feed mode: render inline data directly
  attributes: { type: Array, default: null },
});

const isRemote = computed(() => !!props.server_id);

const remoteMISPAttributesStore = useRemoteMISPAttributesStore();
const { remote_event_attributes, page, size, status } = storeToRefs(
  remoteMISPAttributesStore,
);

if (isRemote.value) {
  remoteMISPAttributesStore.get_remote_server_event_attributes(
    props.server_id,
    props.event_uuid,
    { limit: size.value, page: 0 },
  );
}

// Feed mode: local pagination over the prop array
const localPage = ref(0);

const displayAttributes = computed(() => {
  if (isRemote.value) return remote_event_attributes.value;
  const start = localPage.value * size.value;
  return (props.attributes ?? []).slice(start, start + size.value);
});

const currentPage = computed(() =>
  isRemote.value ? page.value : localPage.value,
);
const hasNextPage = computed(() =>
  isRemote.value
    ? remote_event_attributes.value.length >= size.value
    : (localPage.value + 1) * size.value < (props.attributes ?? []).length,
);

function handleNextPage() {
  if (isRemote.value) {
    page.value += 1;
    remote_event_attributes.value = [];
    remoteMISPAttributesStore.get_remote_server_event_attributes(
      props.server_id,
      props.event_uuid,
      { page: page.value, limit: size.value },
    );
  } else {
    localPage.value += 1;
  }
}

function handlePrevPage() {
  if (isRemote.value) {
    if (page.value == 0) return;
    remote_event_attributes.value = [];
    page.value -= 1;
    remoteMISPAttributesStore.get_remote_server_event_attributes(
      props.server_id,
      props.event_uuid,
      { page: page.value, limit: size.value },
    );
  } else {
    if (localPage.value == 0) return;
    localPage.value -= 1;
  }
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
        <tr
          :key="attribute.uuid || attribute.id"
          v-for="attribute in displayAttributes"
        >
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
        :currentPage="currentPage"
        :hasPrevPage="currentPage > 0"
        :hasNextPage="hasNextPage"
      />
    </div>
  </div>
</template>
