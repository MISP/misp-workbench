<script setup>
import { storeToRefs } from "pinia";
import { useRemoteMISPObjectsStore } from "@/stores";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import Pagination from "@/components/misc/Pagination.vue";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps(["server_id", "event_uuid", "page_size"]);
const remoteMISPObjectsStore = useRemoteMISPObjectsStore();
const { remote_event_objects, page, size, status } = storeToRefs(
  remoteMISPObjectsStore,
);

remoteMISPObjectsStore.get_remote_server_event_objects(
  props.server_id,
  props.event_uuid,
  {
    limit: size.value,
    page: 0,
  },
);

function handleNextPage() {
  page.value = page.value + 1;
  remote_event_objects.value = [];
  remoteMISPObjectsStore.get_remote_server_event_objects(
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
  remote_event_objects.value = [];
  page.value = page.value - 1;
  remoteMISPObjectsStore.get_remote_server_event_objects(
    props.server_id,
    props.event_uuid,
    {
      page: page.value,
      limit: size.value,
    },
  );
}
</script>

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading objects: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <div
      class="mt-2"
      :key="object.Object.uuid"
      v-for="object in remote_event_objects"
    >
      <div class="card" v-if="!object.Object.deleted">
        <div class="card-header">
          {{ object.Object.name }}
        </div>
        <div class="card-body">
          <ObjectAttributesList
            :attributes="object.Object.Attribute"
            :object_id="object.id"
            :default_actions="{
              view: false,
              enrich: false,
              update: false,
              delete: false,
              tag: false,
            }"
          />
        </div>
      </div>
    </div>
  </div>
  <div class="mt-3">
    <Pagination
      @nextPageClick="handleNextPage()"
      @prevPageClick="handlePrevPage()"
      :currentPage="page"
      :hasPrevPage="page > 0"
      :hasNextPage="remote_event_objects.length >= size"
    />
  </div>
</template>
