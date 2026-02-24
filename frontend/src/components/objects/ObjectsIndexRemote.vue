<script setup>
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useRemoteMISPObjectsStore } from "@/stores";
import ObjectAttributesList from "@/components/objects/ObjectAttributesList.vue";
import Pagination from "@/components/misc/Pagination.vue";
import Spinner from "@/components/misc/Spinner.vue";

const props = defineProps({
  // Server mode: fetch from API
  server_id: { type: [String, Number], default: null },
  event_uuid: { type: String, default: null },
  page_size: { type: Number, default: null },
  // Feed mode: render inline data directly
  objects: { type: Array, default: null },
});

const isRemote = computed(() => !!props.server_id);

const remoteMISPObjectsStore = useRemoteMISPObjectsStore();
const { remote_event_objects, page, size, status } = storeToRefs(
  remoteMISPObjectsStore,
);

if (isRemote.value) {
  remoteMISPObjectsStore.get_remote_server_event_objects(
    props.server_id,
    props.event_uuid,
    { limit: size.value, page: 0 },
  );
}

// Feed mode: local pagination over the prop array
const localPage = ref(0);

// Normalise feed objects `{ uuid, name, Attribute }` to match server shape
// `{ Object: { uuid, name, Attribute }, id }` so the template stays uniform.
const displayObjects = computed(() => {
  if (isRemote.value) return remote_event_objects.value;
  const start = localPage.value * size.value;
  return (props.objects ?? [])
    .slice(start, start + size.value)
    .map((obj) => ({ Object: obj, id: obj.uuid }));
});

const currentPage = computed(() =>
  isRemote.value ? page.value : localPage.value,
);
const hasNextPage = computed(() =>
  isRemote.value
    ? remote_event_objects.value.length >= size.value
    : (localPage.value + 1) * size.value < (props.objects ?? []).length,
);

function handleNextPage() {
  if (isRemote.value) {
    page.value += 1;
    remote_event_objects.value = [];
    remoteMISPObjectsStore.get_remote_server_event_objects(
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
    remote_event_objects.value = [];
    page.value -= 1;
    remoteMISPObjectsStore.get_remote_server_event_objects(
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

<template>
  <Spinner v-if="status.loading" />
  <div v-if="status.error" class="text-danger">
    Error loading objects: {{ status.error }}
  </div>
  <div class="table-responsive-sm">
    <div
      class="mt-2"
      :key="object.Object.uuid"
      v-for="object in displayObjects"
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
      :currentPage="currentPage"
      :hasPrevPage="currentPage > 0"
      :hasNextPage="hasNextPage"
    />
  </div>
</template>
